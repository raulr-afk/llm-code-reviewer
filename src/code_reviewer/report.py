"""Render a :class:`Review` as Markdown or JSON."""

from __future__ import annotations

import json
from dataclasses import asdict

from .reviewer import Review, SolutionReview


def _cell(sol: SolutionReview, key: str) -> str:
    return f"{sol.scores[key]:.1f}"


def to_markdown(review: Review) -> str:
    p, a, b = review.problem, review.a, review.b
    verdict = "Tie" if review.verdict == "tie" else f"Solution {review.verdict} wins"
    out = [
        f"# Code review: {p.title}",
        "",
        f"**Verdict:** {verdict}",
        "",
    ]
    if p.description:
        out += [p.description, ""]

    out += [
        "## Scores (0-100)",
        "",
        "| Criterion | Weight | A | B |",
        "|---|---|---|---|",
        f"| Correctness | 60% | {_cell(a, 'correctness')} | {_cell(b, 'correctness')} |",
        f"| Efficiency | 20% | {_cell(a, 'efficiency')} | {_cell(b, 'efficiency')} |",
        f"| Readability | 20% | {_cell(a, 'readability')} | {_cell(b, 'readability')} |",
        f"| **Overall** | | **{_cell(a, 'overall')}** | **{_cell(b, 'overall')}** |",
        "",
        "## Tests",
        "",
        "| Test | A | B |",
        "|---|---|---|",
    ]
    by_name_a = {t.name: t for t in a.run.results}
    by_name_b = {t.name: t for t in b.run.results}
    for t in p.tests:
        ra, rb = by_name_a.get(t.name), by_name_b.get(t.name)
        fmt = lambda r: "n/a" if r is None else ("PASS" if r.passed else "FAIL")  # noqa: E731
        out.append(f"| {t.name} | {fmt(ra)} | {fmt(rb)} |")

    out += [
        "",
        "## Code metrics",
        "",
        "| Metric | A | B |",
        "|---|---|---|",
    ]
    rows = [
        ("Lines of code", "lines_of_code"),
        ("Cyclomatic complexity", "cyclomatic_complexity"),
        ("Max nesting depth", "max_nesting_depth"),
        ("Max loop depth", "max_loop_depth"),
        ("Has docstring", "has_docstring"),
    ]
    for label, attr in rows:
        out.append(f"| {label} | {getattr(a.metrics, attr)} | {getattr(b.metrics, attr)} |")
    out.append(
        f"| Type-hint coverage | {a.metrics.type_hint_ratio:.0%} | {b.metrics.type_hint_ratio:.0%} |"
    )
    out.append(
        f"| Passed-test runtime (s) | {a.run.passed_time:.4f} | {b.run.passed_time:.4f} |"
    )

    if review.summary:
        out += ["", "## Notes", ""] + [f"- {n}" for n in review.summary]

    failures = [(s.label, t) for s in (a, b) for t in s.run.results if t.error]
    if failures:
        out += ["", "## Failure details", ""]
        for label, t in failures[:20]:
            out.append(f"- **{label} / {t.name}**: {t.error}")

    out.append("")
    return "\n".join(out)


def to_json(review: Review) -> str:
    data = {
        "problem": review.problem.title,
        "verdict": review.verdict,
        "solutions": {
            s.label: {
                "path": s.path,
                "scores": s.scores,
                "passed": s.run.passed,
                "total": s.run.total,
                "fatal_error": s.run.fatal_error,
                "metrics": asdict(s.metrics),
                "failures": [asdict(t) for t in s.run.results if not t.passed],
            }
            for s in (review.a, review.b)
        },
        "notes": review.summary,
    }
    return json.dumps(data, indent=2)
