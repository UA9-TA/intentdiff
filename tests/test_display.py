from intentdiff.analyzer import BehaviorChange
from intentdiff.display import display_report


def test_display_report_empty(capsys):
    display_report([], 0, 100)
    captured = capsys.readouterr()
    assert "No unintended behavioral changes detected." in captured.out


def test_display_report_with_changes(capsys):
    changes = [
        BehaviorChange(
            file="auth.py",
            type="logic_operator",
            severity="critical",
            before_behavior="both",
            after_behavior="either",
            explanation="changed and to or",
            line=42,
            before_code="if a and b:",
            after_code="if a or b:",
            confidence=95,
        ),
        BehaviorChange(
            file="utils.py",
            type="default_parameter",
            severity="low",
            before_behavior="5",
            after_behavior="10",
            explanation="timeout increased",
            line=10,
            before_code="def f(t=5):",
            after_code="def f(t=10):",
            confidence=90,
        ),
    ]
    display_report(changes, 2, 90)
    captured = capsys.readouterr()
    assert "CRITICAL" in captured.out
    assert "auth.py" in captured.out
    assert "LOW" in captured.out
    assert "utils.py" in captured.out
    assert "Confidence: 90%" in captured.out
