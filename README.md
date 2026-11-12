# RAG over MITRE ATLAS: AI-security question answering

A retrieval-augmented generation pipeline over [MITRE ATLAS](https://atlas.mitre.org/), the
knowledge base of adversary tactics, techniques, mitigations and real-world case studies against
AI systems. It answers questions about how attacks work, how to defend against them, which incidents
used them, and what to worry about given a system description. Every answer cites the ATLAS
documents it drew from.

**Status: retrieval milestone.** Ingest → chunk → embed → index → top-k retrieval from the command line
are done. Generation and evaluation are next.

**Contributing:** read [docs/COLLABORATION.md](docs/COLLABORATION.md) first. It covers branches,
PR review, data rules and evaluation-question ownership.

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/fix_macos_openmp.py     # macOS only, once after install (see "Known issues")

.venv/bin/python -m rag.build                    # ingest + chunk + embed + index (~30 s on a laptop CPU)
.venv/bin/python -m pytest -q                    # 13 integrity tests

.venv/bin/python -m rag.search "How does an adversary poison a model's training data?" -k 5
.venv/bin/python -m rag.search "..." --mode exact                 # brute-force baseline
.venv/bin/python scripts/milestone_queries.py    # -> docs/milestone.md (5 example queries)
.venv/bin/python -m rag.bench                    # -> docs/bench_minilm.md (build time, QPS, recall vs efSearch)
```

The first run downloads the pinned ATLAS release from GitHub and the embedding model from Hugging
Face. Nothing calls a paid API.

## Pipeline

| stage | module | reads | writes |
|---|---|---|---|
| 1 ingest | `rag/ingest.py` | ATLAS YAML (pinned commit) | `documents`, `doc_links` |
| 2 chunk | `rag/chunk.py` | `documents`, `doc_links` | `chunks` |
| 3 embed | `rag/embed.py` | `chunks` | `embeddings` |
| 4 index | `rag/index.py` | `embeddings` | `data/index/*.faiss`, `*.npy`, `index_rows` |
| 5 retrieve | `rag/search.py` | index files, `index_rows`, `chunks`, `documents` | – |

Every stage reads its input from SQLite (`data/atlas.db`) and writes its output back, never through
in-memory lists, so the chunks, vectors and evaluation labels cannot drift apart. Every stage is
idempotent, so re-running `rag.build` only does missing work.

## Schema ([rag/schema.sql](rag/schema.sql))

The four tables from our proposal keep the proposal's column names. Extra columns are additions.

| table | key | notes |
|---|---|---|
| `documents` | `doc_id` (`atlas:AML.T0051`) | one row per ATLAS object (439), written once; `source_version` = ATLAS release |
| `chunks` | `chunk_id`; `doc_id` → documents | `chunk_id = {doc_id}@{release}#{chunk_config}:{ordinal:04d}` |
| `embeddings` | (`chunk_id`, `model`) | float32 vectors, L2-normalized; `model` lets two embedders share the same chunks |
| `eval_questions` | `q_id` | `relevant_doc_ids` are document-level, so re-chunking never invalidates a label |
| `eval_relevance` | (`q_id`, `doc_id`) | the same labels, one row each, so the database enforces the foreign key |
| `doc_links` | (src, dst, relation, step_id) | ATLAS relationships, including their text (case-study steps, mitigation notes) |
| `index_rows` | (`index_name`, `row_id`) | which `chunk_id` sits at each FAISS row |

Foreign keys are enforced (`PRAGMA foreign_keys = ON` in `rag/db.py`).

## Design decisions

**Corpus pin.** ATLAS release 2026.10 (`dist/v6/ATLAS-2026.10.yaml`, atlas-data commit `f56c146`).
Ingest checks the expected counts: 16 tactics, 221 techniques, 44 mitigations, 77 case studies,
44 entities and 37 software (439 documents), plus 1,734 relationships. The release is part of every
`chunk_id`, so upgrading ATLAS creates new rows instead of overwriting old ones.

**Structure-aware chunking (`struct-v1`).** ATLAS records are short (median ~120 words) but heavily
cross-linked, and much of the useful text sits on the links. Each case-study procedure step, and
each note on how a mitigation applies to a technique, is its own paragraph. Fixed-size windows would
glue unrelated links together and produce far fewer chunks than the corpus has natural units. So
we emit one chunk per natural unit:

| unit_type | from | chunks |
|---|---|---|
| `procedure-step` | case study → technique (`employs`) | 776 |
| `overview` | each document's description + metadata | 606 |
| `mitigates` | mitigation → technique note | 494 |
| `links` | names + ids of related objects ("mitigated by", "used in case studies") | 349 |
| `implements`, `uses` | software/entity notes | 82 |

That makes **2,307 chunks**, averaging 117 tokens with a maximum of 240. Every chunk starts with a
context line (`LLM Prompt Injection: Indirect (AML.T0051.001) | ATLAS technique`), so a chunk
retrieved on its own still names its source. Sub-techniques get their parent's title, because
ATLAS calls them just "Direct" or "Indirect". Units longer than 240 wordpieces are split on
sentences with one sentence of overlap: all-MiniLM-L6-v2 silently truncates at 256, so anything
past the limit would never be embedded. A chunk config never changes after it's written:
`rag.chunk` refuses to overwrite different chunks under the same name. Bump `CHUNK_CONFIG` or
pass `--rebuild`.

**Embeddings.** `all-MiniLM-L6-v2` (384-d) is the baseline. `bge-small-en-v1.5` (384-d, with a
query-side instruction prefix) is configured for the two-embedder comparison:
`python -m rag.build --model bge`.

**Index.** FAISS `IndexHNSWFlat`, inner-product metric on normalized vectors (= cosine), with M=32,
efConstruction=200 and efSearch=64. The exact baseline (`ExactIndex`) is Lab 9's
`BruteForceIndex`, vectorized with numpy so its timing is a fair comparison. Both search the same
vectors in the same row order.

**Recall vs. speed** (single-threaded, one query at a time, 439 title queries, k=10;
full table in [docs/bench_minilm.md](docs/bench_minilm.md)):

| index | efSearch | recall@10 vs exact | ms/query |
|---|---|---|---|
| exact | – | 1.000 | 0.045 |
| HNSW | 16 | 0.949 | 0.017 |
| HNSW | 32 | 0.979 | 0.025 |
| HNSW | 64 | 0.991 | 0.041 |
| HNSW | 128 | 0.998 | 0.073 |

At 2,307 vectors brute force is already fast, and HNSW only pays off at efSearch ≤ 32. Building the
index takes 0.2 s. Embedding the query (≈3 ms) costs about 100× more than searching for it. Numbers
are from one laptop run; re-run `rag.bench` on your machine.

## Known issues

- **macOS OpenMP conflict.** The faiss-cpu and torch wheels each bundle `libomp.dylib`. With both
  loaded, the process aborts ("OMP: Error #15") or segfaults. `scripts/fix_macos_openmp.py` points
  faiss at torch's copy, so only one runtime loads. `rag/__init__.py` also sets
  `OMP_NUM_THREADS=1`, which keeps timings single-threaded and comparable.
- **Exact identifier lookups fail with dense retrieval.** "What does AML.T0051 cover?" returns
  unrelated mitigations, because MiniLM doesn't treat `AML.T0051` as meaningful. We planned to
  test this, and it motivates hybrid BM25 + vector retrieval.

## Data and license

ATLAS data © 2021–2026 MITRE, Apache-2.0. See [data/ATLAS-LICENSE](data/ATLAS-LICENSE) and
[data/NOTICE](data/NOTICE), which describes how our derived database modifies the source. Any shared
copy of `data/atlas.db` must include both files.

## AI assistance

The code in `rag/`, `scripts/` and `tests/` was written with Claude Code (Anthropic) and reviewed by
the team. Each such file says so in its header. The design (schema, chunking strategy, embedder and
index choices) follows our proposal. The evaluation questions are written by team members who read
the ATLAS sources, not by AI.
