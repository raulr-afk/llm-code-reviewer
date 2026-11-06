"""Static analysis of a solution's source code using only the stdlib ``ast``."""

from __future__ import annotations

import ast
from pathlib import Path

from .models import CodeMetrics

_BRANCH_NODES = (
    ast.If, ast.For, ast.While, ast.AsyncFor, ast.ExceptHandler,
    ast.With, ast.IfExp, ast.Assert, ast.comprehension,
)
_NESTING_NODES = (ast.If, ast.For, ast.While, ast.AsyncFor, ast.With, ast.Try)
_LOOP_NODES = (ast.For, ast.While, ast.AsyncFor, ast.ListComp, ast.SetComp,
               ast.DictComp, ast.GeneratorExp)
_ALLOWED_SHORT_NAMES = {"i", "j", "k", "n", "m", "x", "y", "_", "s", "a", "b"}


def _depth(node: ast.AST, kinds: tuple, current: int = 0) -> int:
    best = current
    for child in ast.iter_child_nodes(node):
        nxt = current + 1 if isinstance(child, kinds) else current
        best = max(best, _depth(child, kinds, nxt))
    return best


def analyze_source(source: str) -> CodeMetrics:
    """Return :class:`CodeMetrics` for a string of Python source."""
    metrics = CodeMetrics()
    lines = source.splitlines()
    code_lines = [ln for ln in lines if ln.strip() and not ln.strip().startswith("#")]
    metrics.lines_of_code = len(code_lines)
    if code_lines:
        metrics.avg_line_length = sum(len(ln) for ln in code_lines) / len(code_lines)

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        metrics.parse_error = f"SyntaxError: {exc.msg} (line {exc.lineno})"
        return metrics

    funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    metrics.functions = len(funcs)
    metrics.has_docstring = any(ast.get_docstring(f) for f in funcs) or bool(ast.get_docstring(tree))

    complexity = 1
    for node in ast.walk(tree):
        if isinstance(node, _BRANCH_NODES):
            complexity += 1
        elif isinstance(node, ast.BoolOp):
            complexity += len(node.values) - 1
    metrics.cyclomatic_complexity = complexity
    metrics.max_nesting_depth = _depth(tree, _NESTING_NODES)
    metrics.max_loop_depth = _depth(tree, _LOOP_NODES)

    # type hints: share of function signatures that are annotated
    if funcs:
        annotated = 0
        for f in funcs:
            args = f.args.posonlyargs + f.args.args + f.args.kwonlyargs
            has_arg_hints = all(a.annotation is not None for a in args if a.arg != "self")
            if f.returns is not None and has_arg_hints:
                annotated += 1
        metrics.type_hint_ratio = annotated / len(funcs)

    # naming: share of variable names that are too short to be meaningful
    names = {
        n.id for n in ast.walk(tree)
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
    }
    if names:
        short = [n for n in names if len(n) <= 2 and n not in _ALLOWED_SHORT_NAMES]
        metrics.short_name_ratio = len(short) / len(names)

    return metrics


def analyze_file(path: "str | Path") -> CodeMetrics:
    return analyze_source(Path(path).read_text(encoding="utf-8"))


def readability_score(m: CodeMetrics) -> float:
    """Heuristic 0-100 readability score. Transparent on purpose: see README."""
    if m.parse_error:
        return 0.0
    score = 100.0
    if m.cyclomatic_complexity > 10:
        score -= (m.cyclomatic_complexity - 10) * 3
    if m.max_nesting_depth > 3:
        score -= (m.max_nesting_depth - 3) * 5
    if not m.has_docstring:
        score -= 10
    if m.type_hint_ratio < 1.0:
        score -= 5 * (1.0 - m.type_hint_ratio)
    if m.short_name_ratio > 0.3:
        score -= 10
    if m.avg_line_length > 100:
        score -= 5
    return max(0.0, min(100.0, score))
