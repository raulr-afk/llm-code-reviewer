import json

from code_reviewer.cli import main
from code_reviewer.models import Problem
from code_reviewer.report import to_json, to_markdown
from code_reviewer.reviewer import compare

GOOD = 'def add(a: int, b: int) -> int:\n    """Add."""\n    return a + b\n'
BAD = "def add(a, b):\n    return a * b\n"


def test_correct_solution_wins(problem_file, write_solution):
    review = compare(Problem.from_file(problem_file),
                     write_solution("a.py", BAD), write_solution("b.py", GOOD))
    assert review.verdict == "B"
    assert review.b.scores["correctness"] == 100.0
    assert review.a.scores["correctness"] < 100.0


def test_identical_solutions_tie(problem_file, write_solution):
    review = compare(Problem.from_file(problem_file),
                     write_solution("a.py", GOOD), write_solution("b.py", GOOD))
    assert review.verdict == "tie"


def test_broken_solution_gets_zero_efficiency(problem_file, write_solution):
    review = compare(Problem.from_file(problem_file),
                     write_solution("a.py", "def nope(): pass\n"), write_solution("b.py", GOOD))
    assert review.a.scores["efficiency"] == 0.0
    assert review.a.scores["correctness"] == 0.0
    assert any("could not run" in n for n in review.summary)


def test_reports_render(problem_file, write_solution):
    review = compare(Problem.from_file(problem_file),
                     write_solution("a.py", BAD), write_solution("b.py", GOOD))
    md = to_markdown(review)
    assert "# Code review" in md and "Solution B wins" in md
    data = json.loads(to_json(review))
    assert data["verdict"] == "B"
    assert data["solutions"]["B"]["passed"] == 3


def test_cli_writes_file(problem_file, write_solution, tmp_path, capsys):
    out = tmp_path / "report.md"
    code = main([str(problem_file), str(write_solution("a.py", BAD)),
                 str(write_solution("b.py", GOOD)), "-o", str(out)])
    assert code == 0
    assert out.read_text().startswith("# Code review")


def test_cli_bad_problem_file(tmp_path, capsys):
    bad = tmp_path / "p.json"
    bad.write_text('{"title": "x"}')
    assert main([str(bad), "a.py", "b.py"]) == 2
    assert "missing required key" in capsys.readouterr().err


def test_problem_validation():
    import pytest
    with pytest.raises(ValueError):
        Problem.from_dict({"title": "t", "function_name": "f", "tests": []})
