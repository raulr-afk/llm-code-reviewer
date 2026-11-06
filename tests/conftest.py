import json

import pytest


@pytest.fixture
def problem_file(tmp_path):
    data = {
        "title": "Add two numbers",
        "function_name": "add",
        "timeout": 1,
        "tests": [
            {"name": "positive", "args": [1, 2], "expected": 3},
            {"name": "negative", "args": [-1, -2], "expected": -3},
            {"name": "zero", "args": [0, 0], "expected": 0},
        ],
    }
    path = tmp_path / "problem.json"
    path.write_text(json.dumps(data))
    return path


@pytest.fixture
def write_solution(tmp_path):
    def _write(name, code):
        path = tmp_path / name
        path.write_text(code)
        return path
    return _write
