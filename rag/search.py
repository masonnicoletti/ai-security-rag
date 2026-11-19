"""Stage 5 - RETRIEVE: query -> top-k chunks with their source documents.

AI-assisted: written with Claude Code (Anthropic); reviewed by the team.

Run:  python -m rag.search "What does AML.T0051 cover?" -k 5 --mode hnsw|exact

Every hit is joined index_rows -> chunks -> documents, so each retrieved
chunk names the ATLAS document it came from (the citation the generation
step will use).
"""

from __future__ import annotations

import argparse
import textwrap
import time

from rag import config
from rag.db import connect
from rag.embed import encode_query
from rag.index import load_indexes


class Searcher:
    """Loads one (model, chunk config) index pair once; answers many queries."""

    def __init__(self, model: str = config.DEFAULT_MODEL,
                 chunk_config: str = config.CHUNK_CONFIG, conn=None):
        self.model_short, self.model_id, _ = config.resolve_model(model)
        self.name = config.index_name(self.model_short, chunk_config)
        self.conn = conn or connect()
        self.hnsw, self.exact = load_indexes(self.name)
        self.row_to_chunk = {r["row_id"]: r["chunk_id"] for r in self.conn.execute(
            "SELECT row_id, chunk_id FROM index_rows WHERE index_name = ?", (self.name,))}
        assert len(self.row_to_chunk) == self.hnsw.ntotal == self.exact.ntotal, \
            "index files and index_rows disagree; rebuild with `python -m rag.index`"
        encode_query("warm-up", self.model_short)   # load model now, so query timings exclude it

    def index_for(self, mode: str):
        return {"hnsw": self.hnsw, "exact": self.exact}[mode]

    def search(self, query: str, k: int = 5, mode: str = "hnsw") -> list[dict]:
        qv = encode_query(query, self.model_short)
        pairs = self.index_for(mode).search(qv, k)
        return self.hydrate(pairs)

    def hydrate(self, pairs: list[tuple[float, int]]) -> list[dict]:
        """(score, row) pairs -> dicts carrying chunk text and source document."""
        hits = []
        for rank, (score, row) in enumerate(pairs, start=1):
            r = self.conn.execute(
                """SELECT c.chunk_id, c.unit_type, c.text, d.doc_id, d.title,
                          d.object_type, d.url
                   FROM chunks c JOIN documents d ON d.doc_id = c.doc_id
                   WHERE c.chunk_id = ?""", (self.row_to_chunk[row],)).fetchone()
            hits.append({"rank": rank, "score": score, **dict(r)})
        return hits


def format_hit(hit: dict, width: int = 100, snippet_chars: int = 400) -> str:
    body = hit["text"].split("\n", 1)[-1]          # drop the context header line
    snippet = body[:snippet_chars] + ("..." if len(body) > snippet_chars else "")
    head = (f"#{hit['rank']}  score={hit['score']:.3f}  [{hit['doc_id']}] {hit['title']}"
            f"  ({hit['object_type']}, {hit['unit_type']})")
    return "\n".join([head, f"    chunk: {hit['chunk_id']}",
                      textwrap.indent(textwrap.fill(snippet, width - 4), "    ")])


def main() -> None:
    ap = argparse.ArgumentParser(description="Top-k retrieval over the ATLAS index.")
    ap.add_argument("query")
    ap.add_argument("-k", type=int, default=5)
    ap.add_argument("--mode", choices=["hnsw", "exact"], default="hnsw")
    ap.add_argument("--model", default=config.DEFAULT_MODEL)
    args = ap.parse_args()

    searcher = Searcher(args.model)
    start = time.perf_counter()
    hits = searcher.search(args.query, args.k, args.mode)
    ms = (time.perf_counter() - start) * 1000
    print(f'query: "{args.query}"  ({args.mode}, {searcher.name}, {ms:.1f} ms incl. query embedding)\n')
    for hit in hits:
        print(format_hit(hit) + "\n")


if __name__ == "__main__":
    main()
