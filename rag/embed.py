"""Stage 3 - EMBED: `chunks` -> `embeddings` table.

AI-assisted: written with Claude Code (Anthropic); reviewed by the team.

Run:  python -m rag.embed [--model minilm|bge]

Vectors are L2-normalized at encode time, so inner product == cosine
similarity everywhere downstream (FAISS, the exact baseline, the tests).
They are stored as float32 BLOBs keyed by (chunk_id, model); only chunks
without a vector for this model are encoded, so re-running is cheap.
"""

from __future__ import annotations

import argparse
import sqlite3
import time

import numpy as np

from rag import config
from rag.db import connect

_MODELS: dict = {}


def load_model(model_id: str):
    """Load (once per process) a sentence-transformers model on CPU."""
    if model_id not in _MODELS:
        from sentence_transformers import SentenceTransformer
        _MODELS[model_id] = SentenceTransformer(model_id, device="cpu")
    return _MODELS[model_id]


def encode(texts: list[str], model_id: str, batch_size: int = 64) -> np.ndarray:
    vecs = load_model(model_id).encode(
        texts, batch_size=batch_size, normalize_embeddings=True,
        convert_to_numpy=True, show_progress_bar=False)
    return vecs.astype(np.float32)


def encode_query(query: str, model_name: str) -> np.ndarray:
    """Embed a query, adding the model's query-side prefix (bge needs one)."""
    _, model_id, prefix = config.resolve_model(model_name)
    return encode([prefix + query], model_id)[0]


def to_blob(v: np.ndarray) -> bytes:
    return np.asarray(v, dtype="<f4").tobytes()


def from_blob(b: bytes, dim: int) -> np.ndarray:
    v = np.frombuffer(b, dtype="<f4")
    assert v.shape == (dim,), (v.shape, dim)
    return v


def embed_chunks(conn: sqlite3.Connection, model_name: str,
                 chunk_config: str = config.CHUNK_CONFIG) -> tuple[int, float]:
    """Embed every chunk of `chunk_config` that has no vector for this model yet.
    Returns (number embedded, seconds)."""
    _, model_id, _ = config.resolve_model(model_name)
    todo = conn.execute(
        """SELECT c.chunk_id, c.text FROM chunks c
           WHERE c.chunk_config = ?
             AND NOT EXISTS (SELECT 1 FROM embeddings e
                             WHERE e.chunk_id = c.chunk_id AND e.model = ?)
           ORDER BY c.chunk_id""", (chunk_config, model_id)).fetchall()
    if not todo:
        return 0, 0.0
    start = time.perf_counter()
    vecs = encode([r["text"] for r in todo], model_id)
    seconds = time.perf_counter() - start
    conn.executemany(
        "INSERT INTO embeddings (chunk_id, model, dim, vector) VALUES (?,?,?,?)",
        [(r["chunk_id"], model_id, vecs.shape[1], to_blob(v)) for r, v in zip(todo, vecs)])
    conn.commit()
    return len(todo), seconds


def main() -> None:
    ap = argparse.ArgumentParser(description="Embed chunks with a sentence-transformers model.")
    ap.add_argument("--model", default=config.DEFAULT_MODEL)
    args = ap.parse_args()
    conn = connect()
    n, secs = embed_chunks(conn, args.model)
    _, model_id, _ = config.resolve_model(args.model)
    total = conn.execute("SELECT COUNT(*) FROM embeddings WHERE model = ?", (model_id,)).fetchone()[0]
    rate = f" ({n / secs:.0f} chunks/s)" if n else ""
    print(f"embeddings[{model_id}]: embedded {n} new in {secs:.1f}s{rate}; total {total}")


if __name__ == "__main__":
    main()
