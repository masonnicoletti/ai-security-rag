"""Integrity tests for the built pipeline (run `python -m rag.build` first).

AI-assisted: written with Claude Code (Anthropic); reviewed by the team.

Run:  .venv/bin/python -m pytest -q
"""

from __future__ import annotations

import numpy as np
import pytest

from rag import config
from rag.db import connect
from rag.index import load_indexes, recall_at_k

SHORT, MODEL_ID, PREFIX = config.resolve_model(config.DEFAULT_MODEL)
NAME = config.index_name(SHORT)


@pytest.fixture(scope="module")
def conn():
    if not config.DB_PATH.exists():
        pytest.skip("no database; run `python -m rag.build` first")
    return connect()


@pytest.fixture(scope="module")
def indexes():
    return load_indexes(NAME)


def scalar(conn, sql, *params):
    return conn.execute(sql, params).fetchone()[0]


def test_corpus_counts(conn):
    rows = conn.execute("SELECT object_type, COUNT(*) FROM documents GROUP BY 1").fetchall()
    assert {r[0]: r[1] for r in rows} == config.EXPECTED_COUNTS


def test_foreign_keys_hold(conn):
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_every_chunk_cites_a_document(conn):
    orphans = scalar(conn, """SELECT COUNT(*) FROM chunks c
                              LEFT JOIN documents d ON d.doc_id = c.doc_id WHERE d.doc_id IS NULL""")
    assert orphans == 0


def test_every_document_has_a_chunk(conn):
    assert scalar(conn, """SELECT COUNT(*) FROM documents d WHERE NOT EXISTS
                           (SELECT 1 FROM chunks c WHERE c.doc_id = d.doc_id)""") == 0


def test_chunk_ids_encode_doc_release_config_ordinal(conn):
    for cid, doc_id, ordinal, cfg in conn.execute(
            "SELECT chunk_id, doc_id, ordinal, chunk_config FROM chunks"):
        assert cid == f"{doc_id}@{config.ATLAS_RELEASE}#{cfg}:{ordinal:04d}"


def test_chunks_fit_embedder_window(conn):
    assert scalar(conn, "SELECT MAX(n_tokens) FROM chunks") <= 240


def test_every_chunk_embedded(conn):
    missing = scalar(conn, """SELECT COUNT(*) FROM chunks c WHERE c.chunk_config = ? AND NOT EXISTS
                              (SELECT 1 FROM embeddings e WHERE e.chunk_id = c.chunk_id AND e.model = ?)""",
                     config.CHUNK_CONFIG, MODEL_ID)
    assert missing == 0


def test_index_size_matches_chunks(conn, indexes):
    hnsw, exact = indexes
    n_chunks = scalar(conn, "SELECT COUNT(*) FROM chunks WHERE chunk_config = ?", config.CHUNK_CONFIG)
    n_rows = scalar(conn, "SELECT COUNT(*) FROM index_rows WHERE index_name = ?", NAME)
    assert hnsw.ntotal == exact.ntotal == n_rows == n_chunks


def test_index_rows_match_stored_vectors(conn, indexes):
    """Row i of the saved matrix must be the stored embedding of index_rows[i]."""
    _, exact = indexes
    from rag.embed import from_blob
    for row_id, cid in conn.execute(
            "SELECT row_id, chunk_id FROM index_rows WHERE index_name = ? AND row_id % 97 = 0", (NAME,)):
        dim, blob = conn.execute("SELECT dim, vector FROM embeddings WHERE chunk_id = ? AND model = ?",
                                 (cid, MODEL_ID)).fetchone()
        assert np.allclose(exact.vectors[row_id], from_blob(blob, dim))


def test_self_retrieval_rank_one(indexes):
    """A stored vector used as a query must come back first (exact) and almost always first (HNSW)."""
    hnsw, exact = indexes
    rows = list(range(0, exact.ntotal, 23))
    unique = [r for r in rows if exact.search(exact.vectors[r], 2)[1][0] < 0.9999]  # skip duplicate texts
    assert all(exact.search(exact.vectors[r], 1)[0][1] == r for r in unique)
    hits = sum(hnsw.search(exact.vectors[r], 1)[0][1] == r for r in unique)
    assert hits / len(unique) >= 0.98


def test_hnsw_recall_vs_exact(indexes):
    hnsw, exact = indexes
    rng = np.random.default_rng(0)
    queries = exact.vectors[rng.choice(exact.ntotal, 200, replace=False)]
    queries = queries + rng.normal(0, 0.05, queries.shape).astype(np.float32)   # off-index queries
    queries /= np.linalg.norm(queries, axis=1, keepdims=True)
    rec = np.mean([recall_at_k(hnsw.search(q, 10), exact.search(q, 10), 10) for q in queries])
    assert rec >= 0.95


def test_ingest_is_idempotent(conn):
    from rag import ingest
    before = (scalar(conn, "SELECT COUNT(*) FROM documents"), scalar(conn, "SELECT COUNT(*) FROM doc_links"),
              scalar(conn, "SELECT MIN(ingested_at) FROM documents"))
    ingest.ingest(conn, ingest.load_atlas())
    after = (scalar(conn, "SELECT COUNT(*) FROM documents"), scalar(conn, "SELECT COUNT(*) FROM doc_links"),
             scalar(conn, "SELECT MIN(ingested_at) FROM documents"))
    assert before == after


def test_rechunking_same_config_is_noop(conn):
    from rag import chunk
    rows = chunk.build_chunks(conn, chunk.TokenCounter())
    stored = {r[0]: r[1] for r in conn.execute(
        "SELECT chunk_id, text FROM chunks WHERE chunk_config = ?", (config.CHUNK_CONFIG,))}
    assert {r[0]: r[3] for r in rows} == stored
