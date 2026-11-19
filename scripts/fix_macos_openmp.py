"""macOS only: make faiss-cpu share torch's OpenMP runtime (run once after pip install).

AI-assisted: written with Claude Code (Anthropic); reviewed by the team.

Run:  .venv/bin/python scripts/fix_macos_openmp.py

Why: the faiss-cpu and torch wheels each bundle their own libomp.dylib. When
both load into one process (every query: torch embeds it, faiss searches
it), the second OpenMP runtime aborts with "OMP: Error #15" or segfaults.
This replaces faiss's bundled copy with a symlink to torch's, so only one
runtime is ever loaded. The original is kept as libomp.dylib.orig, and
re-running is a no-op. Re-run it after reinstalling faiss-cpu.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def package_dir(name: str) -> Path:
    spec = importlib.util.find_spec(name)
    if spec is None or spec.origin is None:
        raise SystemExit(f"{name} is not installed in this environment")
    return Path(spec.origin).parent


def main() -> None:
    if sys.platform != "darwin":
        print("not macOS; nothing to do")
        return
    torch_omp = package_dir("torch") / "lib" / "libomp.dylib"
    faiss_omp = package_dir("faiss") / ".dylibs" / "libomp.dylib"
    if not torch_omp.exists() or not (faiss_omp.exists() or faiss_omp.is_symlink()):
        print("expected libomp.dylib files not found; nothing to do")
        return
    if faiss_omp.is_symlink() and faiss_omp.resolve() == torch_omp.resolve():
        print("already linked: faiss uses torch's libomp")
        return
    backup = faiss_omp.with_name("libomp.dylib.orig")
    if not backup.exists():
        faiss_omp.rename(backup)
    else:
        faiss_omp.unlink()
    faiss_omp.symlink_to(torch_omp)
    print(f"linked {faiss_omp} -> {torch_omp}")


if __name__ == "__main__":
    main()
