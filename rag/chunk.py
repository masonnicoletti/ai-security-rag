"""Stage 2 - CHUNK: `documents` + `doc_links` -> `chunks` table.

AI-assisted: written with Claude Code (Anthropic); reviewed by the team.
Hand-written chunker (no LangChain/LlamaIndex), as the assignment requires.

Run:  python -m rag.chunk            (add --rebuild to replace this config's chunks)

Strategy: STRUCTURE-AWARE chunking ("struct-v1")
------------------------------------------------
ATLAS records are short (median ~120 words) but heavily cross-linked, and a
lot of the useful text sits on the links: each case-study procedure step and
each "mitigation M applies to technique T like this" note is its own small
paragraph. So instead of cutting text into fixed windows, we emit one chunk
per natural unit:

  unit_type        source                             one chunk per...
  overview         documents.description + attributes  document (all 439)
  procedure-step   doc_links 'employs'  (CS -> T)       case-study step
  mitigates        doc_links 'mitigates' (M -> T)       mitigation/technique pair
  implements       doc_links 'implements' (S -> T)      software/technique pair
  uses             doc_links 'uses' with text           usage note
  links            doc_links (names + ids only)         technique/tactic/entity/software
                                                        "what is connected to this"

Every chunk starts with a context line naming its document (title, ATLAS id,
type), so a chunk retrieved on its own still says where it came from, and an
id lookup like "AML.T0051" can match it.

A unit longer than the embedder's input limit is split on sentence
boundaries (one sentence of overlap); each piece repeats the context line.
all-MiniLM-L6-v2 truncates input at 256 wordpieces, so the budget is 240
(leaving room for [CLS]/[SEP]). Both of our embedders use the same BERT
uncased vocabulary, so one token count serves both.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass

from transformers import AutoTokenizer

from rag import config
from rag.db import connect

MAX_TOKENS = 240
TOKENIZER_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

TYPE_LABEL = {
    "tactic": "ATLAS tactic",
    "technique": "ATLAS technique",
    "mitigation": "ATLAS mitigation",
    "case-study": "ATLAS case study",
    "entity": "ATLAS entity",
    "software": "ATLAS software",
}


@dataclass
class Unit:
    """A piece of text that should become one chunk (or a few, if too long)."""
    unit_type: str
    header: str   # context line repeated on every piece
    body: str


# ---------------------------------------------------------------- helpers

class TokenCounter:
    def __init__(self, model: str = TOKENIZER_MODEL):
        self.tok = AutoTokenizer.from_pretrained(model)

    def __call__(self, text: str) -> int:
        return len(self.tok.encode(text, add_special_tokens=False))


_SENTENCE = re.compile(r"(?<=[.!?;])\s+|\n+")


def split_to_budget(header: str, body: str, count, budget: int = MAX_TOKENS) -> list[str]:
    """Pack sentences of `body` into pieces of <= budget tokens (header included).

    Greedy packing on sentence boundaries with one sentence of overlap between
    consecutive pieces. A single sentence that is itself over budget is cut
    into word windows as a last resort.
    """
    whole = f"{header}\n{body}".strip()
    if count(whole) <= budget:
        return [whole]

    room = budget - count(header) - 1
    sentences: list[str] = []
    for s in (x.strip() for x in _SENTENCE.split(body)):
        if not s:
            continue
        if count(s) <= room:
            sentences.append(s)
            continue
        words, window = s.split(), []
        for w in words:                      # oversized sentence -> word windows
            if window and count(" ".join(window + [w])) > room:
                sentences.append(" ".join(window))
                window = []
            window.append(w)
        if window:
            sentences.append(" ".join(window))

    pieces: list[list[str]] = []
    current: list[str] = []
    for s in sentences:
        if current and count(" ".join(current + [s])) > room:
            pieces.append(current)
            # overlap: carry the last sentence forward if it still leaves room
            current = [current[-1]] if count(current[-1] + " " + s) <= room else []
        current.append(s)
    if current:
        pieces.append(current)
    return [f"{header}\n{' '.join(p)}" for p in pieces]


def _fmt_list(values) -> str:
    return ", ".join(values) if isinstance(values, list) else str(values)


# ---------------------------------------------------------------- units

class Corpus:
    """In-memory view of documents + links for one release, built from the DB."""

    def __init__(self, conn: sqlite3.Connection):
        self.docs = {r["doc_id"]: dict(r) for r in conn.execute(
            "SELECT * FROM documents WHERE source_version = ? ORDER BY doc_id",
            (config.ATLAS_RELEASE,))}
        self.out = defaultdict(list)   # src -> [link rows]
        self.inc = defaultdict(list)   # dst -> [link rows]
        for r in conn.execute("SELECT * FROM doc_links ORDER BY src_doc_id, step_id, dst_doc_id"):
            r = dict(r)
            self.out[r["src_doc_id"]].append(r)
            self.inc[r["dst_doc_id"]].append(r)
        # sub-technique -> parent technique (titles like "Direct" need the parent)
        self.parent = {r["src_doc_id"]: r["dst_doc_id"]
                       for links in self.out.values() for r in links
                       if r["relation"] == "specializes"}

    def atlas_id(self, doc_id: str) -> str:
        return doc_id.split(":", 1)[1]

    def title(self, doc_id: str) -> str:
        """Display title, e.g. 'LLM Prompt Injection: Indirect' for a sub-technique."""
        t = self.docs[doc_id]["title"]
        if doc_id in self.parent:
            t = f"{self.docs[self.parent[doc_id]]['title']}: {t}"
        return t

    def ref(self, doc_id: str) -> str:
        return f"{self.title(doc_id)} ({self.atlas_id(doc_id)})"

    def header(self, doc_id: str) -> str:
        return f"{self.ref(doc_id)} | {TYPE_LABEL[self.docs[doc_id]['object_type']]}"

    def refs(self, doc_ids) -> str:
        return "; ".join(self.ref(d) for d in doc_ids)

    def linked(self, doc_id: str, relation: str, direction: str = "out") -> list[str]:
        rows = self.out[doc_id] if direction == "out" else self.inc[doc_id]
        key = "dst_doc_id" if direction == "out" else "src_doc_id"
        seen: dict[str, None] = {}
        for r in rows:
            if r["relation"] == relation:
                seen.setdefault(r[key], None)
        return list(seen)

    # ------------------------------------------------------------ per doc

    def units(self, doc_id: str) -> list[Unit]:
        doc = self.docs[doc_id]
        kind = doc["object_type"]
        attrs = json.loads(doc["attributes"])
        header = self.header(doc_id)
        units: list[Unit] = []

        # 1. overview: description + type-specific metadata
        meta = []
        if kind == "technique":
            if doc_id in self.parent:
                meta.append(f"Sub-technique of {self.ref(self.parent[doc_id])}.")
            tactics = self.linked(doc_id, "achieves")
            if tactics:
                meta.append(f"Tactics: {self.refs(tactics)}.")
        if kind == "case-study":
            if doc["case_study_type"]:
                meta.append(f"Case study type: {doc['case_study_type']}.")
            for rel, label in (("attributed-to", "Attributed to"), ("reported-by", "Reported by")):
                ents = self.linked(doc_id, rel)
                if ents:
                    meta.append(f"{label}: {self.refs(ents)}.")
        for key, value in attrs.items():
            meta.append(f"{key.replace('-', ' ').capitalize()}: {_fmt_list(value)}.")
        body = doc["description"] + ("\n" + " ".join(meta) if meta else "")
        units.append(Unit("overview", header, body))

        # 2. one chunk per text-bearing outgoing edge
        for r in self.out[doc_id]:
            dst, rel, desc = r["dst_doc_id"], r["relation"], r["description"]
            if rel == "employs":
                tactic = f" (tactic: {self.title(r['tactic'])})" if r["tactic"] else ""
                units.append(Unit(
                    "procedure-step",
                    f"{header} | procedure step {r['step_id']}",
                    f"In case study {self.title(doc_id)}, step {r['step_id']}{tactic} "
                    f"used technique {self.ref(dst)}. {desc or ''}".strip()))
            elif rel == "mitigates":
                units.append(Unit(
                    "mitigates", header,
                    f"Mitigation {self.ref(doc_id)} against technique {self.ref(dst)}: {desc or ''}".strip()))
            elif rel == "implements":
                units.append(Unit(
                    "implements", header,
                    f"Software {self.ref(doc_id)} implements technique {self.ref(dst)}: {desc or ''}".strip()))
            elif rel == "uses" and desc:
                units.append(Unit(
                    "uses", header, f"{self.ref(doc_id)} uses {self.ref(dst)}: {desc}"))

        # 3. a "links" chunk: what this object connects to (names + ids only),
        #    so "what mitigates X" / "which case studies used X" can land on X itself.
        lines = []
        if kind == "technique":
            pairs = [("Sub-techniques", self.linked(doc_id, "specializes", "in")),
                     ("Mitigated by", self.linked(doc_id, "mitigates", "in")),
                     ("Used in case studies", self.linked(doc_id, "employs", "in")),
                     ("Implemented by software", self.linked(doc_id, "implements", "in"))]
        elif kind == "tactic":
            pairs = [("Techniques for this tactic", self.linked(doc_id, "achieves", "in"))]
        elif kind == "entity":
            pairs = [("Case studies", self.linked(doc_id, "attributed-to", "in")
                      + self.linked(doc_id, "reported-by", "in")),
                     ("Uses", self.linked(doc_id, "uses"))]
        elif kind == "software":
            pairs = [("Used in case studies or by entities", self.linked(doc_id, "uses", "in"))]
        else:
            pairs = []
        for label, ids in pairs:
            if ids:
                lines.append(f"{label}: {self.refs(ids)}.")
        if lines:
            units.append(Unit("links", f"{header} | related ATLAS objects", "\n".join(lines)))
        return units


# ---------------------------------------------------------------- build

def chunk_id_for(doc_id: str, ordinal: int, chunk_config: str = config.CHUNK_CONFIG) -> str:
    return f"{doc_id}@{config.ATLAS_RELEASE}#{chunk_config}:{ordinal:04d}"


def build_chunks(conn: sqlite3.Connection, count) -> list[tuple]:
    corpus = Corpus(conn)
    rows = []
    for doc_id in corpus.docs:
        ordinal = 0
        for unit in corpus.units(doc_id):
            for text in split_to_budget(unit.header, unit.body, count):
                rows.append((chunk_id_for(doc_id, ordinal), doc_id, ordinal, text,
                             count(text), config.CHUNK_CONFIG, unit.unit_type))
                ordinal += 1
    return rows


def write_chunks(conn: sqlite3.Connection, rows: list[tuple], rebuild: bool = False) -> None:
    """Insert chunks for this config, refusing to silently change existing ones.

    A chunk_config name is a promise that its chunks never change. If the
    chunker code changes, either bump config.CHUNK_CONFIG or pass --rebuild
    (which also deletes the now-stale embeddings and index rows).
    """
    cfg = config.CHUNK_CONFIG
    existing = {r[0]: r[1] for r in conn.execute(
        "SELECT chunk_id, text FROM chunks WHERE chunk_config = ?", (cfg,))}
    new = {r[0]: r[3] for r in rows}
    if existing and existing != new:
        if not rebuild:
            raise SystemExit(
                f"chunks for config {cfg!r} differ from what the chunker now produces.\n"
                "Bump CHUNK_CONFIG in rag/config.py, or re-run with --rebuild.")
        stale = "SELECT chunk_id FROM chunks WHERE chunk_config = ?"
        conn.execute(f"DELETE FROM index_rows WHERE chunk_id IN ({stale})", (cfg,))
        conn.execute(f"DELETE FROM embeddings WHERE chunk_id IN ({stale})", (cfg,))
        conn.execute("DELETE FROM chunks WHERE chunk_config = ?", (cfg,))
        existing = {}
    if not existing:
        conn.executemany(
            "INSERT INTO chunks (chunk_id, doc_id, ordinal, text, n_tokens, chunk_config, unit_type)"
            " VALUES (?,?,?,?,?,?,?)", rows)
    conn.commit()


def summarize(conn: sqlite3.Connection) -> None:
    cfg = config.CHUNK_CONFIG
    n, avg, mx = conn.execute(
        "SELECT COUNT(*), AVG(n_tokens), MAX(n_tokens) FROM chunks WHERE chunk_config = ?",
        (cfg,)).fetchone()
    by_type = conn.execute(
        "SELECT unit_type, COUNT(*) FROM chunks WHERE chunk_config = ? GROUP BY unit_type "
        "ORDER BY 2 DESC", (cfg,)).fetchall()
    print(f"chunks[{cfg}]: {n}  avg {avg:.0f} tokens, max {mx}  "
          + "  ".join(f"{t}={c}" for t, c in by_type))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rebuild", action="store_true",
                    help="replace this config's chunks (and their embeddings)")
    args = ap.parse_args()
    conn = connect()
    rows = build_chunks(conn, TokenCounter())
    write_chunks(conn, rows, rebuild=args.rebuild)
    summarize(conn)


if __name__ == "__main__":
    main()
