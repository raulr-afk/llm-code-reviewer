"""Runs inside a child process: loads a solution file and executes the tests.

Input (stdin, JSON):  {"path", "function_name", "timeout", "tests": [...]}
Output (stdout, last line, JSON): {"results": [...]} or {"fatal": "..."}

Running in a separate process keeps crashes, infinite loops and stray prints
in the reviewed code from affecting the reviewer.
"""

import contextlib
import importlib.util
import io
import json
import signal
import sys
import time


class _Timeout(Exception):
    pass


def _alarm_handler(signum, frame):
    raise _Timeout()


def main() -> None:
    payload = json.loads(sys.stdin.read())
    real_stdout = sys.stdout
    sys.setrecursionlimit(5000)

    try:
        spec = importlib.util.spec_from_file_location("solution", payload["path"])
        module = importlib.util.module_from_spec(spec)
        with contextlib.redirect_stdout(io.StringIO()):
            spec.loader.exec_module(module)
        func = getattr(module, payload["function_name"])
    except BaseException as exc:  # noqa: BLE001 - we must report anything
        real_stdout.write(json.dumps({"fatal": f"{type(exc).__name__}: {exc}"}) + "\n")
        return

    use_alarm = hasattr(signal, "setitimer")
    if use_alarm:
        signal.signal(signal.SIGALRM, _alarm_handler)

    results = []
    for test in payload["tests"]:
        entry = {"name": test["name"], "passed": False, "time_s": 0.0, "error": None}
        start = time.perf_counter()
        try:
            if use_alarm:
                signal.setitimer(signal.ITIMER_REAL, payload["timeout"])
            with contextlib.redirect_stdout(io.StringIO()):
                # deep copy via JSON so a solution mutating its input
                # cannot corrupt later tests
                actual = func(*json.loads(json.dumps(test["args"])))
            if use_alarm:
                signal.setitimer(signal.ITIMER_REAL, 0)
            entry["time_s"] = time.perf_counter() - start
            if actual == test["expected"]:
                entry["passed"] = True
            else:
                entry["error"] = f"expected {test['expected']!r}, got {actual!r}"
        except _Timeout:
            entry["time_s"] = time.perf_counter() - start
            entry["error"] = f"timeout after {payload['timeout']}s"
        except RecursionError:
            if use_alarm:
                signal.setitimer(signal.ITIMER_REAL, 0)
            entry["error"] = "RecursionError"
        except BaseException as exc:  # noqa: BLE001
            if use_alarm:
                signal.setitimer(signal.ITIMER_REAL, 0)
            entry["time_s"] = time.perf_counter() - start
            entry["error"] = f"{type(exc).__name__}: {exc}"
        results.append(entry)

    real_stdout.write(json.dumps({"results": results}) + "\n")


if __name__ == "__main__":
    main()
