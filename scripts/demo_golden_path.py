"""
Golden-path verification for demo readiness: runs the backend test suite.
With API and DB up, manually: seed BOM -> enrich -> score -> cross-exposure -> scenario -> export.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    tests = ROOT / "backend" / "tests"
    cmd = [sys.executable, "-m", "pytest", str(tests), "-q"]
    print("Running:", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
