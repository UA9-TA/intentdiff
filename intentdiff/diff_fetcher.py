import subprocess
from typing import Optional


class DiffFetcherError(Exception):
    pass


def fetch_diff(
    staged: bool = False,
    commit: Optional[str] = None,
    from_ref: Optional[str] = None,
    to_ref: Optional[str] = None,
    pr: Optional[int] = None,
) -> str:
    """Fetch unified diff based on provided arguments."""

    if pr is not None:
        return _fetch_pr_diff(pr)

    cmd = ["git", "diff", "--unified=10"]  # Provide enough context lines for the AI

    if commit:
        cmd = ["git", "show", "--unified=10", commit]
    elif from_ref and to_ref:
        cmd.extend([f"{from_ref}..{to_ref}"])
    elif staged:
        cmd.append("--cached")
    else:
        cmd.append("HEAD")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise DiffFetcherError(f"Failed to fetch git diff: {e.stderr}")


def _fetch_pr_diff(pr_number: int) -> str:
    """Fetch diff for a GitHub PR using the gh CLI."""
    try:
        # Check if gh CLI is installed
        subprocess.run(["gh", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise DiffFetcherError(
            "GitHub CLI ('gh') is required to fetch PR diffs. Please install it."
        )

    try:
        result = subprocess.run(
            ["gh", "pr", "diff", str(pr_number)], capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise DiffFetcherError(f"Failed to fetch PR diff using gh CLI: {e.stderr}")
