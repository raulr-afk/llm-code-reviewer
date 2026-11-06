"""Plain dataclasses shared across the package."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional


@dataclass
class TestCase:
    args: List[Any]
    expected: Any
    name: str = ""


@dataclass
class Problem:
    title: str
    function_name: str
    tests: List[TestCase]
    description: str = ""
    timeout: float = 5.0  # seconds, per test case

    @classmethod
    def from_dict(cls, data: dict) -> "Problem":
        for key in ("title", "function_name", "tests"):
            if key not in data:
                raise ValueError(f"Problem file is missing required key: '{key}'")
        if not data["tests"]:
            raise ValueError("Problem must contain at least one test case")
        tests = []
        for i, raw in enumerate(data["tests"], start=1):
            if "args" not in raw or "expected" not in raw:
                raise ValueError(f"Test #{i} needs both 'args' and 'expected'")
            tests.append(
                TestCase(
                    args=raw["args"],
                    expected=raw["expected"],
                    name=raw.get("name", f"test_{i}"),
                )
            )
        return cls(
            title=data["title"],
            function_name=data["function_name"],
            tests=tests,
            description=data.get("description", ""),
            timeout=float(data.get("timeout", 5.0)),
        )

    @classmethod
    def from_file(cls, path: "str | Path") -> "Problem":
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))


@dataclass
class TestResult:
    name: str
    passed: bool
    time_s: float = 0.0
    error: Optional[str] = None  # exception, timeout or wrong-answer detail


@dataclass
class RunResult:
    results: List[TestResult] = field(default_factory=list)
    fatal_error: Optional[str] = None  # import error, crash, global timeout

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def passed_time(self) -> float:
        """Total runtime of the tests that passed (used for efficiency)."""
        return sum(r.time_s for r in self.results if r.passed)


@dataclass
class CodeMetrics:
    lines_of_code: int = 0
    functions: int = 0
    cyclomatic_complexity: int = 1
    max_nesting_depth: int = 0
    max_loop_depth: int = 0  # rough hint for time complexity (n^depth)
    has_docstring: bool = False
    type_hint_ratio: float = 0.0
    short_name_ratio: float = 0.0
    avg_line_length: float = 0.0
    parse_error: Optional[str] = None
