"""Index performance: build time, queries/second, recall-vs-speed for HNSW.

AI-assisted: written with Claude Code (Anthropic); reviewed by the team.

Run:  python -m rag.bench [--model minilm|bge]   -> prints a table, writes docs/bench_<model>.md

Query set: every document title (439 short, natural queries such as
"LLM Prompt Injection"), embedded with the query-side prefix. Titles are not
identical to any chunk, so this measures neighbour-finding, not self-lookup.
Ground truth is the exact baseline's top-k; recall@k is Lab 9's metric.
This is ANN fidelity (does HNSW find what exact search finds?), not answer
relevance - that is what the human-authored eval questions measure.

Timing is single-threaded (OMP_NUM_THREADS=1, see rag/__init__.py) and
one query at a time, matching how the CLI and demo use the index.
"""

from __future__ import annotations

import argparse
import time

import numpy as np

from rag import config
from rag.db import connect
from rag.embed import encode
from rag.index import build_hnsw, load_indexes, load_vectors, recall_at_k

EF_SEARCH_VALUES = [4, 8, 16, 32, 64, 128, 256]
K = 10


def time_queries(index, queries: np.ndarray, k: int, repeats: int = 3):
    """Best-of-`repeats` wall time for one-at-a-time search; returns (qps, results)."""
    best, results = float("inf"), None
    for _ in range(repeats):
        start = time.perf_counter()
        results = [index.search(q, k) for q in queries]
        best = min(best, time.perf_counter() - start)
    return len(queries) / best, results


def run(model_name: str) -> str:
    short, model_id, prefix = config.resolve_model(model_name)
    name = config.index_name(short)
    conn = connect()
    _, vectors = load_vectors(conn, model_id)
    titles = [r[0] for r in conn.execute("SELECT title FROM documents ORDER BY doc_id")]
    queries = encode([prefix + t for t in titles], model_id)

    # build time: average of 3 fresh builds (the saved index is not touched)
    builds = []
    for _ in range(3):
        start = time.perf_counter()
        build_hnsw(vectors)
        builds.append(time.perf_counter() - start)

    hnsw, exact = load_indexes(name)
    exact_qps, truth = time_queries(exact, queries, K)

    lines = [
        f"# Index benchmark: {name}",
        "",
        f"- vectors: {vectors.shape[0]} x {vectors.shape[1]}d; queries: {len(queries)} document titles; k={K}",
        f"- HNSW build (M={config.HNSW_M}, efConstruction={config.HNSW_EF_CONSTRUCTION}): "
        f"{np.mean(builds):.3f}s (mean of 3)",
        "- single-threaded, one query at a time, best of 3 runs; query embedding time excluded",
        "",
        "| index | efSearch | recall@10 vs exact | QPS | ms/query |",
        "|---|---|---|---|---|",
        f"| exact (numpy) | - | 1.000 | {exact_qps:,.0f} | {1000 / exact_qps:.3f} |",
    ]
    for ef in EF_SEARCH_VALUES:
        hnsw.set_ef_search(ef)
        qps, approx = time_queries(hnsw, queries, K)
        rec = np.mean([recall_at_k(a, t, K) for a, t in zip(approx, truth)])
        lines.append(f"| HNSW | {ef} | {rec:.3f} | {qps:,.0f} | {1000 / qps:.3f} |")
    hnsw.set_ef_search(config.HNSW_EF_SEARCH)

    t0 = time.perf_counter()
    for t in titles[:100]:
        encode([prefix + t], model_id)
    embed_ms = (time.perf_counter() - t0) * 10
    lines += ["", f"Query embedding alone: {embed_ms:.1f} ms/query (mean of 100), "
              "which dominates end-to-end latency at this corpus size."]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Benchmark HNSW vs exact search.")
    ap.add_argument("--model", default=config.DEFAULT_MODEL)
    args = ap.parse_args()
    report = run(args.model)
    print(report)
    short, _, _ = config.resolve_model(args.model)
    out = config.ROOT / "docs" / f"bench_{short}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(report)
    print(f"wrote {out.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
