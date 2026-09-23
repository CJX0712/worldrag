"""One-command verification gate: pytest + emoji gate + e2e smoke.

Fully offline by design (default backends need no model, no network, no key).
Emits a machine-readable JSON summary as the LAST stdout line and exits
non-zero on any failure. pytest uses an in-repo basetemp so sandboxed temp
cleanup can never turn a green run into a fake failure.

Author: 晨星
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _run(name: str, cmd: list[str]) -> dict:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.run(
        cmd, cwd=ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace",
    )
    tail = (proc.stdout or "")[-4000:]
    return {"name": name, "cmd": " ".join(cmd), "rc": proc.returncode,
            "ok": proc.returncode == 0, "tail": tail}


def main() -> int:
    stages = [
        _run("pytest", [sys.executable, "-m", "pytest", "-q", "tests",
                        "--basetemp=data/.pytest-tmp", "-p", "no:cacheprovider"]),
        _run("emoji-gate", [sys.executable, "scripts/scan_emoji.py"]),
        _run("e2e-smoke", [sys.executable, "scripts/smoke_e2e.py"]),
    ]
    for stage in stages:
        print(f"===== {stage['name']} (rc={stage['rc']}) =====")
        print(stage["tail"])
    summary = {
        "ok": all(s["ok"] for s in stages),
        "stages": [{"name": s["name"], "rc": s["rc"], "ok": s["ok"]} for s in stages],
    }
    print("VERIFY_SUMMARY " + json.dumps(summary, ensure_ascii=False))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
