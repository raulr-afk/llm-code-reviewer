"""Execute a solution file against a Problem in an isolated subprocess."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from .models import Problem, RunResult, TestResult

_HARNESS = Path(__file__).with_name("_harness.py")


def run_solution(solution_path: "str | Path", problem: Problem) -> RunResult:
    """Run ``solution_path`` against every test in ``problem``.

    Never raises for problems in the reviewed code: crashes, timeouts and
    wrong answers are all reported inside the returned ``RunResult``.
    """
    path = Path(solution_path).resolve()
    if not path.is_file():
        return RunResult(fatal_error=f"File not found: {path}")

    payload = {
        "path": str(path),
        "function_name": problem.function_name,
        "timeout": problem.timeout,
        "tests": [{"name": t.name, "args": t.args, "expected": t.expected} for t in problem.tests],
    }
    # Backstop in case the in-process timer cannot fire (e.g. C-level hang, Windows)
    global_timeout = problem.timeout * len(problem.tests) + 5

    try:
        proc = subprocess.run(
            [sys.executable, "-I", str(_HARNESS)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=global_timeout,
        )
    except subprocess.TimeoutExpired:
        return RunResult(fatal_error=f"Global timeout after {global_timeout:.0f}s")

    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    if not lines:
        detail = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "no output"
        return RunResult(fatal_error=f"Process crashed: {detail}")

    try:
        data = json.loads(lines[-1])
    except json.JSONDecodeError:
        return RunResult(fatal_error="Could not parse harness output")

    if "fatal" in data:
        return RunResult(fatal_error=data["fatal"])

    return RunResult(results=[TestResult(**r) for r in data["results"]])
