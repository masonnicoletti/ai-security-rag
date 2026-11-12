# Team collaboration plan

How we work together on this project from the retrieval milestone (Nov 12) to the final
presentation (Dec 8). It applies to everyone on the team, and to any AI coding assistant a
team member uses. If a rule here gets in the way, change this file in a PR instead of working
around it.

## Who owns what

Each area has one owner who reviews every change to it. Fill in names at the next team meeting.

| area | files | owner |
|---|---|---|
| Ingest and schema | `rag/ingest.py`, `rag/schema.sql`, `rag/db.py`, `rag/config.py` | _TBD_ |
| Chunking | `rag/chunk.py` | _TBD_ |
| Embedding, index, search | `rag/embed.py`, `rag/index.py`, `rag/search.py`, `rag/bench.py` | _TBD_ |
| Generation (LLM answers with citations) | `rag/generate.py` (planned) | _TBD_ |
| Evaluation harness | `rag/evaluate.py`, `eval/` (planned) | _TBD_ |
| Evaluation questions | `eval/questions_<name>.yaml`, one file per author | everyone |
| Report and slides | `docs/report/` (planned) | _TBD_ |

Owning an area means reviewing changes to it, not being the only person who works on it. The
rubric expects every member to be able to explain every line, so make sure each area gets read by
someone other than its owner before the final report.

## Branches and pull requests

- **`main` is the shared, working version.** Nobody pushes directly to `main`. Everything
  arrives through a pull request.
- **Work on your own branch:** `<name>-dev` for ongoing work (e.g. `mason-dev`), or
  `<name>/<topic>` for a focused change (e.g. `mason/bge-embedder`). Branch from the latest
  `main` and keep branches short-lived. Merge at least every few days so we don't drift apart.
- **Every PR needs one approving review from another teammate** before it is merged. Use the
  author's name on the PR (we have no CODEOWNERS file).
- **Keep PRs small enough to review in about 15 minutes.** Split "new chunker + new metric +
  README rewrite" into three PRs.

### Before you open a PR

Run these from a clean state. Delete `data/atlas.db` and `data/index/` first if you changed
ingest, chunking or embedding.

```bash
.venv/bin/python -m rag.build
.venv/bin/python -m pytest -q
```

The PR description says:
1. **What changed and why**, in a few sentences.
2. **How you checked it:** commands run and what they printed (counts, test results).
3. **Numbers that moved:** if a change affects retrieval or answer quality, give the before and
   after on our eval questions.
4. **AI assistance used**, if any (see below).

## Rules that protect shared data

These exist so that every number in the report describes a system we can still rebuild.

- **Schema changes are additive.** Add columns and tables; don't rename or drop the proposal's
  columns (`documents`, `chunks`, `embeddings`, `eval_questions`), because the milestones are
  checked against them. Talk to the schema owner before any change to `rag/schema.sql`.
- **A chunk config never changes once it has been used for a reported number.** To try a
  different chunker, add a new `CHUNK_CONFIG` name (e.g. `struct-v2`) instead of editing
  `struct-v1`. Both can live in the database side by side, which is exactly what the
  two-configuration comparison needs.
- **The corpus stays pinned** to ATLAS 2026.10 (commit `f56c146`). Changing it invalidates
  everyone's results, so it needs agreement from the whole team.
- **Generated data never goes in git.** That includes `data/atlas.db`, `data/index/` and
  `data/raw/`. Anyone can rebuild them with `python -m rag.build`.
- **Every reported number comes from a committed script.** If a table goes in the report, the
  command that produced it goes in the PR, and the output goes under `docs/` (as with
  `docs/bench_minilm.md`). Hand-edited numbers aren't allowed.

## Evaluation questions

The assignment requires that evaluation questions be **written by humans who read the corpus**.
This is the part of the project an AI assistant must never write.

- **One file per author:** `eval/questions_<name>.yaml`. This way two people never edit the same
  file, and the `author` field is always true. Don't edit someone else's questions; ask them.
- **Every question lists its `relevant_doc_ids`** as `atlas:...` ids, checked against the ATLAS
  website or `documents` table. The loader will reject ids that aren't in `documents`.
- **Spread questions across our four categories** (attacks, defenses, real-world evidence,
  threat modeling) plus identifier lookups, and record the category in `q_type`.
- **Target: at least 25 questions in total**, so roughly 9–13 each for a team of 2–3.
- **Partner questions are a held-out test set.** The partner team's 10 questions go in
  `eval/questions_partner.yaml` with `q_type: partner`. We run them and report them, but never
  tune chunk size, k, prompts or anything else on them. Any change made after looking at
  partner results must be stated in the report.

## AI coding assistants

AI assistance is allowed for code, with attribution. Every member must be able to explain
every line at the presentation.

- **Files written with an assistant** carry the header line
  `AI-assisted: written with Claude Code (Anthropic); reviewed by the team.` Mention the
  assistance in the PR.
- **Read and understand AI-written code before you open its PR.** The reviewer should be able to
  ask "why is this line here?" and get an answer from you, not from the assistant.
- **Assistants follow this plan.** `CLAUDE.md` points Claude Code here. Assistants work on a
  branch, never commit to `main`, and never write or edit evaluation questions.
- **No paid LLM APIs** for the project itself. Generation and LLM judging use the course
  endpoint or a local model.

## Milestones

| date | milestone | deliverable | owner |
|---|---|---|---|
| Thu Nov 12 | Retrieval milestone | `docs/milestone.md`, CLI demo | done (Mason) |
| by Tue Nov 17 | Questions drafted | ≥ 25 questions across `eval/questions_*.yaml`; eval loader | everyone / _TBD_ |
| Thu Nov 19 | Question swap | send 10 questions + corpus (`atlas.db` **with** `data/ATLAS-LICENSE` and `data/NOTICE`); run partner's questions | _TBD_ |
| by Mon Nov 30 | Generation and eval harness | cited answers; recall@k, MRR, answer rubric; two-configuration comparison | _TBD_ |
| Thu Dec 3 | Workshop | arrive with eval running; leave with final numbers | everyone |
| Mon Dec 7, 11:59 pm | Final report | 6–8 pages, contribution statement per member | _TBD_ |
| Tue Dec 8 | Presentation | 8 min + live demo; rehearse the demo on the presenter's own laptop | everyone |

## Communication

- **Track tasks as GitHub issues**, assigned to one person, and link them from PRs
  (`Closes #12`). A quick look at open issues should show who is doing what.
- **Hold a short check-in after each milestone** to update the owner table and the milestones
  above.
- **Record decisions affecting everyone** (chunk config, k, embedder, prompt format) in the PR
  that makes them. The report's "design decisions" section is written from those PRs.
