"""Stage 1 - INGEST: ATLAS YAML -> `documents` and `doc_links` tables.

AI-assisted: written with Claude Code (Anthropic); reviewed by the team.

Run:  python -m rag.ingest

What it does
  1. Downloads the pinned ATLAS release (cached in data/raw/, not committed).
  2. Turns each of the 439 ATLAS objects into one `documents` row.
  3. Turns each relationship edge into one `doc_links` row, keeping the
     edge's own text (case-study procedure steps, how a mitigation applies
     to a technique) because that text is where much of the answer lives.

Idempotent: documents are "written once" (INSERT ... ON CONFLICT DO NOTHING),
so re-running ingest never rewrites rows or changes ingested_at.
"""

from __future__ import annotations

import json
import re
import sqlite3
import urllib.request
from collections import Counter
from datetime import datetime, timezone

import yaml

from rag import config
from rag.db import connect

# YAML section name -> object_type value used in ATLAS and in our table.
SECTIONS = {
    "tactics": "tactic",
    "techniques": "technique",
    "mitigations": "mitigation",
    "case-studies": "case-study",
    "entities": "entity",
    "software": "software",
}

# object_type -> path segment on atlas.mitre.org, for citation URLs.
URL_PATHS = {
    "tactic": "tactics",
    "technique": "techniques",
    "mitigation": "mitigations",
    "case-study": "studies",
    "entity": "entities",
    "software": "software",
}


def doc_id_for(atlas_id: str) -> str:
    """Namespace ATLAS ids so a future second source can't collide."""
    return f"atlas:{atlas_id}"


# ---------------------------------------------------------------- text cleanup

# [Name](/techniques/AML.T0051.000)  -> "Name (AML.T0051.000)"
_INTERNAL_LINK = re.compile(r"\[([^\]]+)\]\(/[a-z-]+/(AML\.[A-Z]+\d+(?:\.\d+)?)\)")
# [paper by Le et al.](https://...)   -> "paper by Le et al."
_EXTERNAL_LINK = re.compile(r"\[([^\]]+)\]\((?:https?://|/)[^)]*\)")
# citation markers like [[arxiv-1]]   -> removed
_CITATION = re.compile(r"\[\[[^\]]+\]\]")


def clean_text(text: str | None) -> str:
    """Strip markdown link syntax but keep the words and the ATLAS ids.

    Keeping the id inline matters: it lets a query such as "AML.T0051.001"
    match text that *mentions* that technique, not just its own record.
    """
    if not text:
        return ""
    text = _INTERNAL_LINK.sub(r"\1 (\2)", text)
    text = _EXTERNAL_LINK.sub(r"\1", text)
    text = _CITATION.sub("", text)
    # Keep paragraph breaks, fold single line breaks into spaces.
    paragraphs = [" ".join(p.split()) for p in re.split(r"\n\s*\n", text)]
    return "\n\n".join(p for p in paragraphs if p)


# ---------------------------------------------------------------- load

def download(force: bool = False) -> None:
    """Fetch the pinned YAML once; later runs reuse the cached copy."""
    if config.RAW_YAML.exists() and not force:
        return
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"downloading {config.ATLAS_URL}")
    with urllib.request.urlopen(config.ATLAS_URL, timeout=120) as resp:
        config.RAW_YAML.write_bytes(resp.read())


def load_atlas() -> dict:
    download()
    with open(config.RAW_YAML, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------- write

def _date(value) -> str | None:
    return None if value is None else str(value)


# Type-specific fields worth showing to the embedder and the reader. Anything
# else (uuids, reference lists) stays out of the chunks.
ATTRIBUTE_FIELDS = [
    "platforms", "maturity",                       # techniques
    "categories", "lifecycle-phases",              # mitigations
    "actor", "target", "reporter", "start-date",   # case studies
    "entity-type", "software-type", "software-categories", "aliases",
]


def attributes_for(obj: dict) -> dict:
    return {k: (str(obj[k]) if k == "start-date" else obj[k])
            for k in ATTRIBUTE_FIELDS if obj.get(k) not in (None, "", [])}


def ingest(conn: sqlite3.Connection, atlas: dict) -> Counter:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    source = f"{config.ATLAS_REPO}@{config.ATLAS_COMMIT[:7]}"
    counts: Counter = Counter()
    known_ids: set[str] = set()

    for section, object_type in SECTIONS.items():
        for atlas_id, obj in atlas[section].items():
            assert obj["object-type"] == object_type, (atlas_id, obj["object-type"])
            known_ids.add(atlas_id)
            counts[object_type] += 1
            conn.execute(
                """INSERT INTO documents (doc_id, source, source_version, object_type,
                       title, url, modified_date, ingested_at, created_date,
                       case_study_type, license, description, attributes)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(doc_id) DO NOTHING""",
                (
                    doc_id_for(atlas_id), source, config.ATLAS_RELEASE, object_type,
                    obj["name"],
                    f"https://atlas.mitre.org/{URL_PATHS[object_type]}/{atlas_id}",
                    _date(obj.get("modified-date")), now,
                    _date(obj.get("created-date")),
                    obj.get("type") if object_type == "case-study" else None,
                    config.ATLAS_LICENSE,
                    clean_text(obj.get("description")),
                    json.dumps(attributes_for(obj)),
                ),
            )

    # Relationships: {source_id: {relation: [edge, ...]}}.
    # 'sequences' edges start at the matrix object (not a document) and only
    # order the tactics, so they are skipped.
    for src, by_relation in atlas["relationships"].items():
        for relation, edges in by_relation.items():
            for e in edges:
                if e["source"] not in known_ids or e["target"] not in known_ids:
                    counts["skipped-edge"] += 1
                    continue
                conn.execute(
                    """INSERT INTO doc_links (src_doc_id, dst_doc_id, relation,
                           step_id, tactic, description)
                       VALUES (?,?,?,?,?,?)
                       ON CONFLICT DO NOTHING""",
                    (
                        doc_id_for(e["source"]), doc_id_for(e["target"]), relation,
                        e.get("step-id") or "",
                        doc_id_for(e["tactic"]) if e.get("tactic") else None,
                        clean_text(e.get("description")) or None,
                    ),
                )
                counts[f"edge:{relation}"] += 1
    conn.commit()
    return counts


def check_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Assert the table holds exactly the expected corpus for this release."""
    rows = conn.execute(
        "SELECT object_type, COUNT(*) FROM documents WHERE source_version = ? "
        "GROUP BY object_type", (config.ATLAS_RELEASE,)).fetchall()
    actual = {r[0]: r[1] for r in rows}
    assert actual == config.EXPECTED_COUNTS, f"unexpected corpus counts: {actual}"
    return actual


def main() -> None:
    conn = connect()
    counts = ingest(conn, load_atlas())
    actual = check_counts(conn)
    print(f"documents: {sum(actual.values())}  {actual}")
    edges = {k[5:]: v for k, v in counts.items() if k.startswith("edge:")}
    n_links = conn.execute("SELECT COUNT(*) FROM doc_links").fetchone()[0]
    print(f"doc_links: {n_links}  {edges}  (skipped {counts['skipped-edge']} matrix edges)")


if __name__ == "__main__":
    main()
