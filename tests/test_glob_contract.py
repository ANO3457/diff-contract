"""Examples and diagnostics for the existing fnmatch glob contract."""

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, ValidationError

from diff_contract.contract import ContractRule
from diff_contract.engine import RulesEngine


@pytest.mark.parametrize(
    "pattern,path,expected",
    [
        ("src/**", "src/main.py", True),
        ("src/**", "src/pkg/main.py", True),
        ("src/*", "src/pkg/main.py", True),
        ("*.py", "src/main.py", True),
        ("tests/test_?.py", "tests/test_a.py", True),
        ("tests/test_?.py", "tests/test_ab.py", False),
        ("docs/[ab]*.md", "docs/api.md", True),
        ("docs/[!_]*.md", "docs/_draft.md", False),
        ("docs/[!_]*.md", "docs/guide.md", True),
        ("!important.txt", "important.txt", False),
        ("!important.txt", "!important.txt", True),
    ],
)
def test_documented_glob_semantics(pattern, path, expected):
    rule = ContractRule(name="example", allow=(pattern,), deny=(pattern,))
    assert rule.matches_allow(path) is expected
    assert rule.matches_deny(path) is expected


def test_denied_file_names_the_matching_pattern():
    rule = ContractRule(name="protect", deny=("private/**", "*.env"))
    violation, = RulesEngine([rule]).check(["config.env"])
    assert "*.env" in violation.message
    assert "private/**" not in violation.message


def test_outside_scope_names_the_allowed_patterns():
    rule = ContractRule(name="docs", allow=("docs/**", "README.md"))
    violation, = RulesEngine([rule]).check(["src/app.py"])
    assert "docs/**" in violation.message
    assert "README.md" in violation.message


def validator():
    schema = json.loads((Path(__file__).parents[1] / "schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_schema_accepts_example_contracts():
    check = validator()
    for path in (Path(__file__).parents[1] / "examples").glob("*.yml"):
        check.validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    check.validate({})
    check.validate({"$schema": "./schema.json", "rules": [{"allow": None, "max_files": None}]})
    check.validate({"rules": [{"on_violation": "info", "max_lines": 0}]})


@pytest.mark.parametrize(
    "data",
    [
        {"version": 2},
        {"rules": "not a list"},
        {"rules": [{"allow": "src/**"}]},
        {"rules": [{"deny": [42]}]},
        {"rules": [{"max_files": -1}]},
        {"rules": [{"max_lines": True}]},
        {"rules": [{"on_violation": "blocks"}]},
        {"rules": [{"alow": ["src/**"]}]},
    ],
)
def test_schema_rejects_mistyped_contracts(data):
    with pytest.raises(ValidationError):
        validator().validate(data)
