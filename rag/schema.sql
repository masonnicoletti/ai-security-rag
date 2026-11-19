-- Schema for the ATLAS RAG pipeline.
-- AI-assisted: written with Claude Code (Anthropic); reviewed by the team.
--
-- The four proposal tables (documents, chunks, embeddings, eval_questions)
-- keep the proposal's column names exactly; extra columns are additive.
-- Three helper tables (eval_relevance, doc_links, index_rows) exist so the
-- database, not Python lists, enforces the joins the evaluation depends on.

PRAGMA foreign_keys = ON;

-- One row per ATLAS object, written at ingestion.
CREATE TABLE IF NOT EXISTS documents (
    doc_id          TEXT PRIMARY KEY,      -- 'atlas:AML.T0051'
    source          TEXT NOT NULL,         -- 'mitre-atlas/atlas-data@<commit>'
    source_version  TEXT NOT NULL,         -- ATLAS release, e.g. '2026.10'
    object_type     TEXT NOT NULL,         -- tactic | technique | mitigation | case-study | entity | software
    title           TEXT NOT NULL,
    url             TEXT,
    modified_date   TEXT,
    ingested_at     TEXT NOT NULL,
    -- additions beyond the proposal
    created_date    TEXT,
    case_study_type TEXT,                  -- 'Exercise' / 'Incident' for case studies, else NULL
    license         TEXT NOT NULL,
    description     TEXT NOT NULL,         -- cleaned description (input to the chunker)
    attributes      TEXT NOT NULL          -- JSON: type-specific fields (platforms, actor, ...)
);

-- Retrievable units. chunk_id = '{doc_id}@{release}#{chunk_config}:{ordinal:04d}'
-- so ids stay stable across runs and different chunkers never collide.
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id     TEXT PRIMARY KEY,
    doc_id       TEXT NOT NULL REFERENCES documents(doc_id),
    ordinal      INTEGER NOT NULL,         -- position within its document (per config)
    text         TEXT NOT NULL,
    n_tokens     INTEGER NOT NULL,         -- counted with the embedder's tokenizer
    -- additions
    chunk_config TEXT NOT NULL,            -- e.g. 'struct-v1'
    unit_type    TEXT NOT NULL,            -- overview | procedure-step | mitigates | implements | links | ...
    UNIQUE (doc_id, chunk_config, ordinal)
);
CREATE INDEX IF NOT EXISTS chunks_by_doc ON chunks(doc_id);

-- One vector per (chunk, model): lets us compare embedders on identical chunks.
CREATE TABLE IF NOT EXISTS embeddings (
    chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),
    model    TEXT NOT NULL,
    dim      INTEGER NOT NULL,
    vector   BLOB NOT NULL,                -- float32 little-endian, L2-normalized
    PRIMARY KEY (chunk_id, model)
);

-- Human-authored evaluation questions (labels are document-level, so
-- re-chunking never invalidates them).
CREATE TABLE IF NOT EXISTS eval_questions (
    q_id             TEXT PRIMARY KEY,
    question         TEXT NOT NULL,
    relevant_doc_ids TEXT NOT NULL,        -- JSON list, as in the proposal
    author           TEXT NOT NULL,
    q_type           TEXT                  -- attack | defense | evidence | threat-model | id-lookup | partner
);

-- Same labels as eval_questions.relevant_doc_ids, one row per (question, doc),
-- so the foreign key to documents is enforced rather than trusted.
CREATE TABLE IF NOT EXISTS eval_relevance (
    q_id   TEXT NOT NULL REFERENCES eval_questions(q_id),
    doc_id TEXT NOT NULL REFERENCES documents(doc_id),
    PRIMARY KEY (q_id, doc_id)
);

-- ATLAS relationships between objects (employs, mitigates, achieves, ...).
-- Many edges carry their own text (a case-study procedure step, how a
-- mitigation applies to a technique); the chunker turns those into chunks.
CREATE TABLE IF NOT EXISTS doc_links (
    src_doc_id  TEXT NOT NULL REFERENCES documents(doc_id),
    dst_doc_id  TEXT NOT NULL REFERENCES documents(doc_id),
    relation    TEXT NOT NULL,
    step_id     TEXT NOT NULL DEFAULT '',  -- case-study step ('S03'); '' for other relations
    tactic      TEXT,                      -- tactic id for case-study steps
    description TEXT,                      -- cleaned edge text, may be NULL
    PRIMARY KEY (src_doc_id, dst_doc_id, relation, step_id)
);

-- FAISS stores vectors by integer row; this maps each row back to its chunk.
CREATE TABLE IF NOT EXISTS index_rows (
    index_name TEXT NOT NULL,              -- e.g. 'hnsw:minilm:struct-v1'
    row_id     INTEGER NOT NULL,
    chunk_id   TEXT NOT NULL REFERENCES chunks(chunk_id),
    PRIMARY KEY (index_name, row_id)
);
