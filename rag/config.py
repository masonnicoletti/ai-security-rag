"""Central configuration: corpus pin, file paths, model and index settings.

AI-assisted: written with Claude Code (Anthropic); reviewed by the team.

Everything that changes the *meaning* of a stored row (corpus release, chunking
config, embedding model) lives here and is written into the rows themselves,
so numbers in the report can always be traced back to the exact setup.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------- corpus pin
# We pin an exact commit of mitre-atlas/atlas-data so every teammate (and the
# partner team) ingests byte-identical data. Bumping the release is a
# deliberate change: chunk_ids embed the release, so old rows never collide.
ATLAS_REPO = "mitre-atlas/atlas-data"
ATLAS_COMMIT = "f56c1468731d6428e5bf875263b4643b46d67437"
ATLAS_RELEASE = "2026.10"
ATLAS_PATH = f"dist/v6/ATLAS-{ATLAS_RELEASE}.yaml"
ATLAS_URL = f"https://raw.githubusercontent.com/{ATLAS_REPO}/{ATLAS_COMMIT}/{ATLAS_PATH}"
ATLAS_LICENSE = "Apache-2.0 (Copyright 2021-2026 MITRE)"

# Expected object counts for this release; ingest asserts them so a silent
# parsing bug can't shrink the corpus without us noticing.
EXPECTED_COUNTS = {
    "tactic": 16,
    "technique": 221,
    "mitigation": 44,
    "case-study": 77,
    "entity": 44,
    "software": 37,
}

# ---------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
RAW_YAML = RAW_DIR / f"ATLAS-{ATLAS_RELEASE}.yaml"
DB_PATH = DATA_DIR / "atlas.db"
INDEX_DIR = DATA_DIR / "index"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

# ---------------------------------------------------------------- chunking
# Name of the active chunking configuration. It is part of every chunk_id, so
# a new chunker version gets new ids instead of overwriting old ones.
CHUNK_CONFIG = "struct-v1"

# ---------------------------------------------------------------- embedding
DEFAULT_MODEL = "minilm"
MODELS = {
    # short name -> (HF model id, prefix added to *queries* only)
    "minilm": ("sentence-transformers/all-MiniLM-L6-v2", ""),
    # bge models are trained with an instruction prefix on the query side.
    "bge": ("BAAI/bge-small-en-v1.5",
            "Represent this sentence for searching relevant passages: "),
}


def resolve_model(name: str) -> tuple[str, str, str]:
    """Accept a short name ('minilm') or a full HF id.

    Returns (short_name, hf_model_id, query_prefix). The HF id is what goes in
    embeddings.model; the short name is used in index file names.
    """
    for short, (model_id, prefix) in MODELS.items():
        if name in (short, model_id):
            return short, model_id, prefix
    raise SystemExit(f"unknown model {name!r}; add it to MODELS in rag/config.py")


def index_name(model_short: str, chunk_config: str = CHUNK_CONFIG) -> str:
    """Name of one vector set: (embedding model, chunk config). HNSW and the
    exact baseline share it because they store rows in the same order."""
    return f"{model_short}:{chunk_config}"


# ---------------------------------------------------------------- HNSW
HNSW_M = 32               # graph degree: higher = better recall, more memory
HNSW_EF_CONSTRUCTION = 200  # build-time beam width: higher = better graph, slower build
HNSW_EF_SEARCH = 64       # query-time beam width: the recall-vs-speed knob
