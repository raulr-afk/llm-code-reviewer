"""Combine execution results and static metrics into a scored comparison."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from .metrics import analyze_file, readability_score
from .models import CodeMetrics, Problem, RunResult
from .runner import run_solution

# Weights must sum to 1.0
WEIGHTS = {"correctness": 0.6, "efficiency": 0.2, "readability": 0.2}
TIE_MARGIN = 2.0  # points
# Timing noise guards: below this total runtime, speed differences are meaningless,
# and ratios above NOISE_RATIO are treated as "equally fast".
NEGLIGIBLE_RUNTIME_S = 0.05
NOISE_RATIO = 0.8


@dataclass
class SolutionReview:
    label: str
    path: str
    run: RunResult
    metrics: CodeMetrics
    scores: Dict[str, float] = field(default_factory=dict)

    @property
    def overall(self) -> float:
        return self.scores.get("overall", 0.0)


@dataclass
class Review:
    problem: Problem
    a: SolutionReview
    b: SolutionReview
    verdict: str  # "A", "B" or "tie"
    summary: List[str] = field(default_factory=list)


def _efficiency_scores(a: RunResult, b: RunResult) -> tuple:
    """Relative efficiency: the faster correct solution gets 100.

    Only passed tests count, and only if the solution passed something.
    A solution that passes nothing scores 0 so speed cannot rescue it.
    """
    ta, tb = a.passed_time, b.passed_time
    if a.passed == 0 and b.passed == 0:
        return 0.0, 0.0
    if a.passed == 0:
        return 0.0, 100.0
    if b.passed == 0:
        return 100.0, 0.0
    # compare on tests both solved, so a solution is not rewarded for failing hard tests
    common = {r.name for r in a.results if r.passed} & {r.name for r in b.results if r.passed}
    if common:
        ta = sum(r.time_s for r in a.results if r.name in common)
        tb = sum(r.time_s for r in b.results if r.name in common)
    if max(ta, tb) < NEGLIGIBLE_RUNTIME_S:
        return 100.0, 100.0
    fastest = max(min(ta, tb), 1e-9)
    eff_a = 100.0 * fastest / max(ta, 1e-9)
    eff_b = 100.0 * fastest / max(tb, 1e-9)
    # within the noise band -> treat as equal
    if min(eff_a, eff_b) / 100.0 >= NOISE_RATIO:
        return 100.0, 100.0
    return eff_a, eff_b


def _build_summary(r: Review) -> List[str]:
    notes: List[str] = []
    for sol in (r.a, r.b):
        if sol.run.fatal_error:
            notes.append(f"Solution {sol.label} could not run: {sol.run.fatal_error}")
        elif sol.run.passed < sol.run.total:
            failed = [t.name for t in sol.run.results if not t.passed]
            notes.append(
                f"Solution {sol.label} failed {len(failed)}/{sol.run.total} tests: "
                + ", ".join(failed[:5]) + ("..." if len(failed) > 5 else "")
            )
        if sol.metrics.parse_error:
            notes.append(f"Solution {sol.label}: {sol.metrics.parse_error}")
        if sol.metrics.max_loop_depth >= 3:
            notes.append(
                f"Solution {sol.label} has loops nested {sol.metrics.max_loop_depth} deep "
                "(possible O(n^3) behaviour)."
            )
        if not sol.metrics.has_docstring:
            notes.append(f"Solution {sol.label} has no docstring.")
    return notes


def _score(sol: SolutionReview, efficiency: float) -> None:
    correctness = sol.run.pass_rate * 100.0
    readability = readability_score(sol.metrics)
    overall = (
        WEIGHTS["correctness"] * correctness
        + WEIGHTS["efficiency"] * efficiency
        + WEIGHTS["readability"] * readability
    )
    sol.scores = {
        "correctness": round(correctness, 1),
        "efficiency": round(efficiency, 1),
        "readability": round(readability, 1),
        "overall": round(overall, 1),
    }


def compare(problem: Problem, path_a: "str | Path", path_b: "str | Path") -> Review:
    """Run, analyse and score two solutions to ``problem``."""
    a = SolutionReview("A", str(path_a), run_solution(path_a, problem), analyze_file(path_a))
    b = SolutionReview("B", str(path_b), run_solution(path_b, problem), analyze_file(path_b))

    eff_a, eff_b = _efficiency_scores(a.run, b.run)
    _score(a, eff_a)
    _score(b, eff_b)

    diff = a.overall - b.overall
    verdict = "tie" if abs(diff) < TIE_MARGIN else ("A" if diff > 0 else "B")
    review = Review(problem=problem, a=a, b=b, verdict=verdict)
    review.summary = _build_summary(review)
    return review
