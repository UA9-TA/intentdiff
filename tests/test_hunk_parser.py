import pytest
from pathlib import Path

from intentdiff.hunk_parser import parse_diff

def test_parse_logic_operator_change():
    patch_path = Path("tests/fixtures/logic_operator_change.patch")
    with open(patch_path, "r") as f:
        diff_text = f.read()

    hunks = parse_diff(diff_text)

    assert len(hunks) == 1
    hunk = hunks[0]
    assert hunk.file == "auth/validators.py"
    assert "if not user.is_active and not user.is_banned:" in hunk.before_lines
    assert "if not user.is_active or not user.is_banned:" in hunk.after_lines

def test_parse_boundary_condition_change():
    patch_path = Path("tests/fixtures/boundary_condition_change.patch")
    with open(patch_path, "r") as f:
        diff_text = f.read()

    hunks = parse_diff(diff_text)

    assert len(hunks) == 1
    hunk = hunks[0]
    assert hunk.file == "payment/processor.py"
    assert "if amount <= MAX_SINGLE_TXN:" in hunk.before_lines
    assert "if amount < MAX_SINGLE_TXN:" in hunk.after_lines
