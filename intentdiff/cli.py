import os
import stat
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from intentdiff.analyzer import BehaviorChange, analyze_hunks
from intentdiff.config import set_api_key as config_set_api_key
from intentdiff.diff_fetcher import DiffFetcherError, fetch_diff
from intentdiff.display import display_report
from intentdiff.explainer import explain_change
from intentdiff.hunk_parser import parse_diff
from intentdiff.risk_scorer import filter_changes_by_risk

app = typer.Typer(name="intentdiff", help="Detect silent behavioral changes in AI-generated code")
console = Console()


@app.command()
def check(
    staged: bool = False,
    commit: Optional[str] = None,
    from_ref: Optional[str] = None,
    to_ref: Optional[str] = None,
    pr: Optional[int] = None,
    risk: str = "medium",  # low | medium | high
):
    """Analyze diff for unintended behavioral changes."""
    try:
        raw_diff = fetch_diff(staged=staged, commit=commit, from_ref=from_ref, to_ref=to_ref, pr=pr)
    except DiffFetcherError as e:
        console.print(f"[red]Error fetching diff:[/red] {e}")
        raise typer.Exit(1)

    if not raw_diff.strip():
        console.print("No changes found to analyze.")
        raise typer.Exit(0)

    hunks = parse_diff(raw_diff)
    if not hunks:
        console.print("No code changes found in diff.")
        raise typer.Exit(0)

    # Count unique files
    files_analyzed = len(set(h.file for h in hunks))

    with console.status("[bold green]Analyzing code behavior with Claude..."):
        try:
            results = analyze_hunks(hunks)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    all_changes = []
    overall_confidence = 100

    for r in results:
        if r.has_behavioral_change:
            # Convert to dict for filtering
            changes_dict = [c.__dict__ for c in r.changes]
            filtered_dicts = filter_changes_by_risk(changes_dict, risk)

            # Convert back to BehaviorChange
            for d in filtered_dicts:
                # Add back the fields that might be missing from dict but required by dataclass
                # Since we populated everything in analyzer, this should be fine
                all_changes.append(BehaviorChange(**d))

            overall_confidence = min(overall_confidence, r.confidence)

    display_report(all_changes, files_analyzed, overall_confidence)


@app.command()
def explain(location: str):
    """Deep-dive explanation of one behavioral change (file:line)."""
    try:
        file, line_str = location.split(":")
        line = int(line_str)
    except ValueError:
        console.print("[red]Error:[/red] Location must be in format file:line (e.g., auth.py:42)")
        raise typer.Exit(1)

    with console.status("[bold green]Generating explanation..."):
        try:
            explanation = explain_change(file, line)
            console.print("\n[bold]Detailed Explanation[/bold]")
            console.print("──────────────────────────────────────────────────")
            console.print(explanation)
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)


@app.command()
def install_hook():
    """Install as git pre-commit hook."""
    git_dir = Path(".git")
    if not git_dir.exists() or not git_dir.is_dir():
        console.print("[red]Error:[/red] Not in a git repository.")
        raise typer.Exit(1)

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    hook_path = hooks_dir / "pre-commit"

    hook_script = """#!/bin/sh
# intentdiff pre-commit hook
echo "Running IntentDiff on staged changes..."
intentdiff check --staged --risk high
if [ $? -ne 0 ]; then
    echo "IntentDiff found potential behavioral changes."
    # Optionally exit 1 to block commit
    # exit 1
fi
"""
    with open(hook_path, "w") as f:
        f.write(hook_script)

    # Make executable
    st = os.stat(hook_path)
    os.chmod(hook_path, st.st_mode | stat.S_IEXEC)

    console.print("[green]Successfully installed pre-commit hook at .git/hooks/pre-commit[/green]")


@app.command()
def config(api_key: str):
    """Set Anthropic API key."""
    config_set_api_key(api_key, global_config=True)
    console.print(
        "[green]Successfully saved Anthropic API key to ~/.intentdiff/config.toml[/green]"
    )


if __name__ == "__main__":
    app()
