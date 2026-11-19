"""RAG over MITRE ATLAS. AI-assisted: written with Claude Code (Anthropic); reviewed by the team.

Process-wide settings that must be in place before torch or faiss is imported:

* OMP_NUM_THREADS=1 - faiss-cpu and torch each ship their own OpenMP runtime;
  on macOS, loading both and running a faiss search segfaults. One OpenMP
  thread avoids it, and also makes QPS measurements single-threaded and
  therefore comparable between HNSW and the exact baseline.
* TOKENIZERS_PARALLELISM=false - silences a HuggingFace fork warning.
"""

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
