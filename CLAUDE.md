# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A class final project (Advanced Databases for Data Science): a RAG pipeline over the MITRE ATLAS
corpus (AI-security tactics, techniques, mitigations, case studies, entities, software). Stages:
ingest → chunk → embed → index → retrieve → generate → evaluate. Status: retrieval milestone done
(ingest through CLI search, tests, benchmark); generation and evaluation are next. See README.md.

## Commands

Use the project venv (`.venv/`, Python 3.13, pinned in `requirements.txt`).

```bash
.venv/bin/python scripts/fix_macos_openmp.py   # macOS, once after pip install (faiss+torch OpenMP clash)
.venv/bin/python -m rag.build [--model bge]    # ingest -> chunk -> embed -> index (idempotent)
.venv/bin/python -m rag.search "query" -k 5 --mode hnsw|exact [--model minilm|bge]
.venv/bin/python -m rag.bench                  # build time, QPS, recall vs efSearch -> docs/bench_<model>.md
.venv/bin/python scripts/milestone_queries.py  # -> docs/milestone.md
.venv/bin/python -m pytest -q                  # needs a built DB; single test: -k test_hnsw_recall_vs_exact
.venv/bin/python -m rag.chunk --rebuild        # replace this config's chunks AND delete their embeddings/index rows
```

Without `scripts/fix_macos_openmp.py`, any process that loads both torch and faiss can abort with
"OMP: Error #15" or segfault. `rag/__init__.py` sets `OMP_NUM_THREADS=1`, and `rag/index.py`
imports torch before faiss; keep both.

`data/raw/`, `data/atlas.db` and `data/index/` are generated. Delete `data/atlas.db` to start
over (ingest uses `ON CONFLICT DO NOTHING`, so it never rewrites existing rows).

## Architecture

- **The database is the source of truth.** Every stage reads its inputs from SQLite
  (`data/atlas.db`, schema in [rag/schema.sql](rag/schema.sql)) and writes its outputs back, never
  from in-memory lists. `rag/db.py:connect()` applies the schema and enables `PRAGMA foreign_keys`;
  always connect through it.
- **Proposal tables:** `documents`, `chunks`, `embeddings`, `eval_questions`. The column names
  were submitted in the course proposal and the milestone is graded against them. Add columns,
  don't rename them. Helper tables: `doc_links` (ATLAS relationships, including edge text),
  `eval_relevance` (FK-enforced mirror of `eval_questions.relevant_doc_ids`) and `index_rows`
  (FAISS row → `chunk_id`).
- **Ids:** `doc_id = "atlas:<ATLAS id>"`; `chunk_id = "{doc_id}@{release}#{chunk_config}:{ordinal:04d}"`.
  Eval labels are document-level, so re-chunking never invalidates them.
- **A chunk config is immutable.** If chunker output changes, bump `CHUNK_CONFIG` in
  [rag/config.py](rag/config.py) or run `--rebuild`; `write_chunks` refuses to change chunks silently.
- **Corpus pin:** `ATLAS_COMMIT` / `ATLAS_RELEASE` in `rag/config.py`. Ingest asserts
  `EXPECTED_COUNTS`, so update both together when changing the release.
- **Chunking is structure-aware** ([rag/chunk.py](rag/chunk.py)). Each document gets one
  `overview` chunk, plus one chunk per text-bearing link: `procedure-step` (case study → technique),
  `mitigates`, `implements` and `uses`. Techniques, tactics, entities and software also get a
  `links` chunk listing related objects. Every chunk starts with a context line naming its
  title and ATLAS id. Units over 240 MiniLM wordpieces are split on sentences with one sentence
  of overlap.
- **Embedders:** `minilm` (all-MiniLM-L6-v2) and `bge` (bge-small-en-v1.5, which needs a
  query-side prefix). Both are in `config.MODELS`; `embeddings.model` allows comparing them on
  identical chunks.
- **Index** ([rag/index.py](rag/index.py)): FAISS `IndexHNSWFlat` (inner product on normalized
  vectors) plus `ExactIndex`, a numpy brute-force baseline. Both return `(score, row)` best-first
  (the Lab 9 `BruteForceIndex.search` contract) over the same rows. An index is named by
  `config.index_name(model, chunk_config)`; `index_rows` maps rows to `chunk_id`, and
  `rag/search.py:Searcher.hydrate` joins rows → chunks → documents for citations.

## Assignment rules that constrain code changes

- Chunking, indexing and retrieval must be hand-written. LangChain and LlamaIndex are allowed only
  for the generation step.
- Every AI-written module carries an attribution header ("AI-assisted: written with Claude Code").
  Keep that header on new modules.
- Evaluation questions must be written by humans who read the corpus. Don't generate them.
- No paid LLM APIs: generation uses the course's OpenAI-compatible endpoint (`LLM_BASE_URL`,
  `LLM_API_KEY`, `LLM_MODEL`, as in Lab 10's `micro_rag.answer`) or a local model.
- Corpus license: Apache-2.0 (MITRE). Keep `data/ATLAS-LICENSE` and the attribution when sharing.
