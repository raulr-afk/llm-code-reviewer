from code_reviewer.models import Problem
from code_reviewer.runner import run_solution


def test_correct_solution_passes_all(problem_file, write_solution):
    sol = write_solution("ok.py", "def add(a, b):\n    return a + b\n")
    result = run_solution(sol, Problem.from_file(problem_file))
    assert result.fatal_error is None
    assert result.passed == result.total == 3


def test_wrong_answer_is_reported(problem_file, write_solution):
    sol = write_solution("bad.py", "def add(a, b):\n    return a - b\n")
    result = run_solution(sol, Problem.from_file(problem_file))
    assert result.passed == 1  # only the zero case
    failing = [r for r in result.results if not r.passed]
    assert "expected" in failing[0].error


def test_exception_is_captured(problem_file, write_solution):
    sol = write_solution("boom.py", "def add(a, b):\n    raise ValueError('nope')\n")
    result = run_solution(sol, Problem.from_file(problem_file))
    assert result.passed == 0
    assert "ValueError" in result.results[0].error


def test_missing_function_is_fatal(problem_file, write_solution):
    sol = write_solution("wrong_name.py", "def plus(a, b):\n    return a + b\n")
    result = run_solution(sol, Problem.from_file(problem_file))
    assert result.fatal_error is not None
    assert "add" in result.fatal_error


def test_syntax_error_is_fatal(problem_file, write_solution):
    sol = write_solution("syntax.py", "def add(a, b)\n    return a + b\n")
    result = run_solution(sol, Problem.from_file(problem_file))
    assert "SyntaxError" in result.fatal_error


def test_infinite_loop_times_out(problem_file, write_solution):
    sol = write_solution("loop.py", "def add(a, b):\n    while True:\n        pass\n")
    result = run_solution(sol, Problem.from_file(problem_file))
    assert result.passed == 0
    assert all("timeout" in r.error for r in result.results)


def test_prints_do_not_break_output(problem_file, write_solution):
    sol = write_solution("noisy.py", "print('hi')\ndef add(a, b):\n    print('x')\n    return a + b\n")
    result = run_solution(sol, Problem.from_file(problem_file))
    assert result.passed == 3


def test_input_mutation_does_not_leak(write_solution, tmp_path):
    problem = Problem.from_dict({
        "title": "t", "function_name": "pop_first",
        "tests": [
            {"name": "one", "args": [[1, 2]], "expected": 1},
            {"name": "two", "args": [[1, 2]], "expected": 1},
        ],
    })
    sol = write_solution("mut.py", "def pop_first(xs):\n    return xs.pop(0)\n")
    assert run_solution(sol, problem).passed == 2


def test_missing_file(problem_file, tmp_path):
    result = run_solution(tmp_path / "nope.py", Problem.from_file(problem_file))
    assert "File not found" in result.fatal_error
