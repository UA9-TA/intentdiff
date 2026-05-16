from intentdiff.risk_scorer import filter_changes_by_risk, get_severity


def test_get_severity():
    assert get_severity("logic_operator") == "critical"
    assert get_severity("boundary_condition") == "medium"
    assert get_severity("default_parameter") == "low"
    assert get_severity("unknown_type") == "medium"


def test_filter_changes_by_risk():
    changes = [
        {"type": "logic_operator", "severity": "critical", "file": "a.py"},
        {"type": "boundary_condition", "severity": "medium", "file": "b.py"},
        {"type": "default_parameter", "severity": "low", "file": "c.py"},
    ]

    # Low risk filters none
    filtered_low = filter_changes_by_risk(changes, "low")
    assert len(filtered_low) == 3

    # Medium risk filters out low
    filtered_medium = filter_changes_by_risk(changes, "medium")
    assert len(filtered_medium) == 2
    assert "c.py" not in [c["file"] for c in filtered_medium]

    # High risk filters out medium and low
    filtered_high = filter_changes_by_risk(changes, "high")
    assert len(filtered_high) == 1
    assert filtered_high[0]["file"] == "a.py"
