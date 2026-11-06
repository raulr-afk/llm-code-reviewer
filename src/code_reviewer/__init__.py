"""llm-code-reviewer: compare two Python solutions to the same problem."""

from .models import CodeMetrics, Problem, RunResult, TestCase, TestResult
from .reviewer import Review, compare

__all__ = [
    "CodeMetrics",
    "Problem",
    "Review",
    "RunResult",
    "TestCase",
    "TestResult",
    "compare",
]
__version__ = "0.1.0"
