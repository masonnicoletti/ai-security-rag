"""Retrieval milestone: run 5 example queries, write docs/milestone.md.

AI-assisted: written with Claude Code (Anthropic); reviewed by the team.

Run:  python scripts/milestone_queries.py [--model minilm] [-k 5]

The queries are the example questions from our proposal, one per question
category plus the identifier lookup. They are demo queries, NOT evaluation
questions (those are human-authored and live in eval_questions).
For each query we show the HNSW top-k and how many of them exact search agrees on.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag import config  # noqa: E402
from rag.embed import encode_query  # noqa: E402
from rag.search import Searcher  # noqa: E402

QUERIES = [
    ("Understanding attacks",
     "What is LLM prompt injection, and how does indirect injection differ from direct injection?"),
    ("Defending systems",
     "What mitigations does ATLAS recommend against model extraction through an API?"),
    ("Real-world evidence",
     "Which documented incidents involved evading a malware classifier?"),
    ("Threat modeling",
     "My app retrieves documents from a shared wiki and passes them to an LLM that can send "
     "emails. What attacks should I consider?"),
    ("Identifier lookup", "What does AML.T0051 cover?"),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=config.DEFAULT_MODEL)
    ap.add_argument("-k", type=int, default=5)
    args = ap.parse_args()

    s = Searcher(args.model)
    out = [f"# Retrieval milestone: 5 example queries",
           "",
           f"Index `{s.name}` ({s.hnsw.ntotal} chunks), FAISS HNSW (M={config.HNSW_M}, "
           f"efSearch={config.HNSW_EF_SEARCH}), top-{args.k}. ATLAS release {config.ATLAS_RELEASE}.",
           "Each hit shows its chunk_id and the source document it cites.", ""]
    for i, (category, q) in enumerate(QUERIES, start=1):
        qv = encode_query(q, s.model_short)
        t0 = time.perf_counter()
        pairs = s.hnsw.search(qv, args.k)
        ms = (time.perf_counter() - t0) * 1000
        exact_rows = {r for _, r in s.exact.search(qv, args.k)}
        agree = sum(r in exact_rows for _, r in pairs)
        out += [f"## {i}. {category}", "", f"> {q}", "",
                f"HNSW search {ms:.2f} ms; {agree}/{args.k} of these are also in exact top-{args.k}.", "",
                "| rank | score | source document | chunk type | chunk_id |", "|---|---|---|---|---|"]
        hits = s.hydrate(pairs)
        for h in hits:
            out.append(f"| {h['rank']} | {h['score']:.3f} | [{h['doc_id']}]({h['url']}) {h['title']} "
                       f"({h['object_type']}) | {h['unit_type']} | `{h['chunk_id']}` |")
        out += ["", "<details><summary>chunk text</summary>", ""]
        for h in hits:
            out += [f"**#{h['rank']}** `{h['chunk_id']}`", "", "```", h["text"], "```", ""]
        out += ["</details>", ""]

    path = config.ROOT / "docs" / "milestone.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text("\n".join(out))
    print(f"wrote {path.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
