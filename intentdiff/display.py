from typing import List

from rich.console import Console

from intentdiff.analyzer import BehaviorChange

console = Console()


def display_report(changes: List[BehaviorChange], files_analyzed: int, confidence: int):
    """Print the IntentDiff Behavioral Change Report."""

    console.print("\n[bold]IntentDiff — Behavioral Change Report[/bold]")
    console.print("──────────────────────────────────────────────────")

    # Summary
    critical_count = sum(1 for c in changes if c.severity == "critical")
    medium_count = sum(1 for c in changes if c.severity == "medium")
    low_count = sum(1 for c in changes if c.severity == "low")

    console.print(f"✦ Files analyzed      {files_analyzed} changed files")

    counts = []
    if critical_count > 0:
        counts.append(f"{critical_count} critical")
    if medium_count > 0:
        counts.append(f"{medium_count} medium")
    if low_count > 0:
        counts.append(f"{low_count} low")

    counts_str = f" ({', '.join(counts)})" if counts else ""
    console.print(f"✦ Behavioral changes  {len(changes)} detected{counts_str}\n")

    if not changes:
        console.print("[green]No unintended behavioral changes detected.[/green]")
        console.print("──────────────────────────────────────────────────")
        return

    # Group by severity
    grouped = {"critical": [], "medium": [], "low": []}
    for c in changes:
        grouped[c.severity].append(c)

    for severity, color in [("critical", "red"), ("medium", "yellow"), ("low", "cyan")]:
        items = grouped[severity]
        if not items:
            continue

        console.print(
            f"  ── [bold {color}]{severity.upper()}[/bold {color}] " + "─" * (45 - len(severity))
        )

        for item in items:
            console.print(f"  [bold]{item.file}[/bold]  line {item.line}")

            # Simple before/after lines if available, else omit
            # Since before_code/after_code might be multiple lines, we just show the summary here

            explanation = f"""  ⚠ {item.explanation}
    Before: {item.before_behavior}
    After:  {item.after_behavior}"""

            console.print(f"[{color}]{explanation}[/{color}]\n")

    console.print(f"✦ Confidence: {confidence}%")
    console.print("──────────────────────────────────────────────────")
    console.print("Run `intentdiff explain <file>:<line>` for detailed fix suggestion.")
