"""Command line interface: ``code-reviewer problem.json a.py b.py``."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from .models import Problem
from .report import to_json, to_markdown
from .reviewer import compare


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="code-reviewer",
        description="Compare two Python solutions on correctness, efficiency and readability.",
    )
    parser.add_argument("problem", help="Path to the problem JSON file")
    parser.add_argument("solution_a", help="Path to solution A (.py)")
    parser.add_argument("solution_b", help="Path to solution B (.py)")
    parser.add_argument("-f", "--format", choices=["md", "json"], default="md")
    parser.add_argument("-o", "--output", help="Write the report to a file instead of stdout")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        problem = Problem.from_file(args.problem)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    review = compare(problem, args.solution_a, args.solution_b)
    text = to_markdown(review) if args.format == "md" else to_json(review)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"Report written to {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
