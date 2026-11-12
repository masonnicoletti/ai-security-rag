"""One command to rebuild everything: ingest -> chunk -> embed -> index.

AI-assisted: written with Claude Code (Anthropic); reviewed by the team.

Run:  python -m rag.build [--model minilm] [--model bge]

Every stage is idempotent, so re-running only does missing work.
"""

from __future__ import annotations

import argparse

from rag import chunk, config, embed, index, ingest
from rag.db import connect


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", action="append",
                    help="embedder(s) to build (default: minilm); repeatable")
    args = ap.parse_args()
    models = args.model or [config.DEFAULT_MODEL]

    conn = connect()
    print("== ingest")
    ingest.ingest(conn, ingest.load_atlas())
    counts = ingest.check_counts(conn)
    print(f"documents: {sum(counts.values())}  {counts}")

    print("== chunk")
    chunk.write_chunks(conn, chunk.build_chunks(conn, chunk.TokenCounter()))
    chunk.summarize(conn)

    for model in models:
        print(f"== embed + index ({model})")
        n, secs = embed.embed_chunks(conn, model)
        print(f"embedded {n} new chunks in {secs:.1f}s")
        s = index.build_and_save(conn, model)
        print(f"index[{s.name}]: {s.n_vectors} vectors x {s.dim}d, HNSW build {s.hnsw_build_s:.2f}s")


if __name__ == "__main__":
    main()
