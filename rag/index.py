"""Stage 4 - INDEX: `embeddings` -> FAISS HNSW index + exact baseline.

AI-assisted: written with Claude Code (Anthropic); reviewed by the team.

Run:  python -m rag.index [--model minilm|bge]

Two indexes over the SAME vectors, in the SAME row order:
  * ExactIndex  - brute force: score = V @ q for every row, keep the top k.
                  Correct by construction; the ground truth for recall.
                  (Lab 9's BruteForceIndex, vectorized with numpy so its
                  timing is a fair baseline rather than a Python-loop strawman.)
  * HNSW        - faiss.IndexHNSWFlat with inner-product metric. Vectors are
                  normalized, so inner product == cosine. Approximate: it walks
                  a layered proximity graph and may miss true neighbours;
                  efSearch trades that recall against speed.

FAISS only knows integer row numbers, so `index_rows` records which chunk_id
sits at each row. Files written to data/index/:
  {model}_{config}.hnsw.faiss   the HNSW graph + vectors
  {model}_{config}.vectors.npy  the matrix the exact baseline scans
"""

from __future__ import annotations

import argparse
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

# torch must be loaded BEFORE faiss: both bundle an OpenMP runtime, and on
# macOS loading torch second aborts the process (see also rag/__init__.py).
import torch  # noqa: F401  (imported for its side effect on load order)
import faiss
import numpy as np

from rag import config
from rag.db import connect
from rag.embed import from_blob


# ---------------------------------------------------------------- exact baseline

class ExactIndex:
    """Brute-force top-k. search() follows Lab 9's BruteForceIndex contract:
    a list of (similarity, row) pairs, best first, ties broken by row id."""

    def __init__(self, vectors: np.ndarray):
        self.vectors = np.ascontiguousarray(vectors, dtype=np.float32)

    @property
    def ntotal(self) -> int:
        return self.vectors.shape[0]

    def search(self, query: np.ndarray, k: int) -> list[tuple[float, int]]:
        return self.search_batch(query[None, :], k)[0]

    def search_batch(self, queries: np.ndarray, k: int) -> list[list[tuple[float, int]]]:
        k = min(k, self.ntotal)
        scores = queries @ self.vectors.T                     # (n_queries, n_rows): every comparison
        out = []
        for row in scores:
            top = np.argpartition(-row, k - 1)[:k]            # unordered top k in O(n)
            top = sorted(top, key=lambda i: (-row[i], i))      # (score desc, id asc)
            out.append([(float(row[i]), int(i)) for i in top])
        return out


# ---------------------------------------------------------------- HNSW

class HNSWIndex:
    """Thin wrapper so both indexes expose the same search() signature."""

    def __init__(self, index: faiss.IndexHNSWFlat):
        self.index = index

    @property
    def ntotal(self) -> int:
        return self.index.ntotal

    def set_ef_search(self, ef: int) -> None:
        self.index.hnsw.efSearch = ef

    def search(self, query: np.ndarray, k: int) -> list[tuple[float, int]]:
        return self.search_batch(query[None, :], k)[0]

    def search_batch(self, queries: np.ndarray, k: int) -> list[list[tuple[float, int]]]:
        scores, ids = self.index.search(np.ascontiguousarray(queries, dtype=np.float32), k)
        return [[(float(s), int(i)) for s, i in zip(srow, irow) if i >= 0]
                for srow, irow in zip(scores, ids)]


def build_hnsw(vectors: np.ndarray, m: int = config.HNSW_M,
               ef_construction: int = config.HNSW_EF_CONSTRUCTION,
               ef_search: int = config.HNSW_EF_SEARCH) -> HNSWIndex:
    index = faiss.IndexHNSWFlat(vectors.shape[1], m, faiss.METRIC_INNER_PRODUCT)
    index.hnsw.efConstruction = ef_construction
    index.add(np.ascontiguousarray(vectors, dtype=np.float32))
    index.hnsw.efSearch = ef_search
    return HNSWIndex(index)


def recall_at_k(approx: list[tuple[float, int]], exact: list[tuple[float, int]], k: int) -> float:
    """Lab 9's metric: fraction of the true top-k the approximate search found."""
    truth = {i for _, i in exact[:k]}
    found = {i for _, i in approx[:k]}
    return len(truth & found) / k


# ---------------------------------------------------------------- persistence

def paths_for(name: str) -> tuple[Path, Path]:
    stem = name.replace(":", "_")
    return (config.INDEX_DIR / f"{stem}.hnsw.faiss", config.INDEX_DIR / f"{stem}.vectors.npy")


def load_vectors(conn: sqlite3.Connection, model_id: str,
                 chunk_config: str = config.CHUNK_CONFIG) -> tuple[list[str], np.ndarray]:
    """All vectors for (model, chunk_config), in chunk_id order."""
    rows = conn.execute(
        """SELECT e.chunk_id, e.dim, e.vector FROM embeddings e
           JOIN chunks c ON c.chunk_id = e.chunk_id
           WHERE e.model = ? AND c.chunk_config = ? ORDER BY e.chunk_id""",
        (model_id, chunk_config)).fetchall()
    if not rows:
        raise SystemExit(f"no embeddings for {model_id} / {chunk_config}; run `python -m rag.embed` first")
    ids = [r["chunk_id"] for r in rows]
    return ids, np.stack([from_blob(r["vector"], r["dim"]) for r in rows])


@dataclass
class BuildStats:
    name: str
    n_vectors: int
    dim: int
    hnsw_build_s: float


def build_and_save(conn: sqlite3.Connection, model_name: str,
                   chunk_config: str = config.CHUNK_CONFIG) -> BuildStats:
    short, model_id, _ = config.resolve_model(model_name)
    name = config.index_name(short, chunk_config)
    chunk_ids, vectors = load_vectors(conn, model_id, chunk_config)

    start = time.perf_counter()
    hnsw = build_hnsw(vectors)
    build_s = time.perf_counter() - start

    config.INDEX_DIR.mkdir(parents=True, exist_ok=True)
    hnsw_path, vec_path = paths_for(name)
    faiss.write_index(hnsw.index, str(hnsw_path))
    np.save(vec_path, vectors)

    # Row -> chunk_id mapping, replaced wholesale so it always matches the files.
    conn.execute("DELETE FROM index_rows WHERE index_name = ?", (name,))
    conn.executemany("INSERT INTO index_rows (index_name, row_id, chunk_id) VALUES (?,?,?)",
                     [(name, i, cid) for i, cid in enumerate(chunk_ids)])
    conn.commit()
    return BuildStats(name, len(chunk_ids), vectors.shape[1], build_s)


def load_indexes(name: str) -> tuple[HNSWIndex, ExactIndex]:
    hnsw_path, vec_path = paths_for(name)
    if not hnsw_path.exists():
        raise SystemExit(f"index {name} not built; run `python -m rag.index`")
    return HNSWIndex(faiss.read_index(str(hnsw_path))), ExactIndex(np.load(vec_path))


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the FAISS HNSW index and exact baseline.")
    ap.add_argument("--model", default=config.DEFAULT_MODEL)
    args = ap.parse_args()
    s = build_and_save(connect(), args.model)
    print(f"index[{s.name}]: {s.n_vectors} vectors x {s.dim}d, HNSW build {s.hnsw_build_s:.2f}s "
          f"(M={config.HNSW_M}, efConstruction={config.HNSW_EF_CONSTRUCTION})")


if __name__ == "__main__":
    main()
