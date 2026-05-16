from typing import Any, Dict, List

CRITICAL = ["logic_operator", "null_guard_removed", "security_check"]
MEDIUM = ["boundary_condition", "exception_scope", "return_value"]
LOW = ["default_parameter", "type_coercion", "loop_condition"]


def get_severity(change_type: str) -> str:
    """Determine severity based on change type."""
    if change_type in CRITICAL:
        return "critical"
    elif change_type in MEDIUM:
        return "medium"
    elif change_type in LOW:
        return "low"
    return "medium"  # default


def filter_changes_by_risk(changes: List[Dict[str, Any]], risk_level: str) -> List[Dict[str, Any]]:
    """
    Filter changes based on the specified risk level.
    risk_level: 'low', 'medium', or 'high'
    """
    risk_level = risk_level.lower()

    if risk_level == "low":
        # Show all changes
        return changes

    filtered = []
    for change in changes:
        severity = change.get("severity", get_severity(change.get("type", ""))).lower()

        if risk_level == "high":
            if severity == "critical":
                filtered.append(change)
        elif risk_level == "medium":
            if severity in ["critical", "medium"]:
                filtered.append(change)

    return filtered
