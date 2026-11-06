from code_reviewer.metrics import analyze_source, readability_score


def test_simple_function_metrics():
    m = analyze_source('def f(x: int) -> int:\n    """Doc."""\n    return x\n')
    assert m.functions == 1
    assert m.cyclomatic_complexity == 1
    assert m.has_docstring
    assert m.type_hint_ratio == 1.0


def test_branches_increase_complexity():
    src = "def f(x):\n    if x > 0 and x < 10:\n        return 1\n    for i in range(x):\n        pass\n"
    m = analyze_source(src)
    assert m.cyclomatic_complexity == 4  # base + if + and + for


def test_loop_depth_detects_nesting():
    src = "def f(n):\n    for i in range(n):\n        for j in range(n):\n            for k in range(n):\n                pass\n"
    assert analyze_source(src).max_loop_depth == 3


def test_syntax_error_gives_zero_readability():
    m = analyze_source("def f(:\n")
    assert m.parse_error
    assert readability_score(m) == 0.0


def test_documented_typed_code_scores_higher():
    good = analyze_source('def f(x: int) -> int:\n    """Doc."""\n    return x\n')
    bad = analyze_source("def f(x):\n    return x\n")
    assert readability_score(good) > readability_score(bad)


def test_short_names_penalised():
    src = "def f(data):\n    qq = 1\n    zz = 2\n    ww = 3\n    return qq + zz + ww\n"
    assert analyze_source(src).short_name_ratio > 0.3
