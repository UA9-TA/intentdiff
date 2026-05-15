# Jules Build Prompt — IntentDiff v1.0

## What You Are Building

**IntentDiff** is an open-source CLI tool that uses Claude AI to semantically analyze git diffs and detect when AI-generated code has silently changed the *intent* or *behavior* of your codebase — not just the text.

The core problem: A standard `git diff` shows what changed in text. It cannot tell you that the AI swapped `and` for `or` in a security check, removed a null guard that was load-bearing, changed a `<=` to `<` in a rate limiter, or dropped an exception handler without replacing it. These changes pass syntax checks, linters, and sometimes even tests — they only fail in production.

IntentDiff reads the diff, understands what the original code *did*, understands what the new code *does*, and flags every place where the behavior changed in a way the developer may not have intended.

**Target:** Top GitHub trending. This is the #1 unsolved problem for every team using AI-assisted coding.

---

## Core User Flow

```bash
# Install
pip install intentdiff

# Analyze the last commit
intentdiff check

# Analyze staged changes before committing
intentdiff check --staged

# Analyze a specific commit or range
intentdiff check --commit abc1234
intentdiff check --from main --to feature/auth-rewrite

# Analyze a GitHub PR
intentdiff check --pr 42

# Set risk threshold (default: medium)
intentdiff check --risk low      # flag everything
intentdiff check --risk high     # only flag critical behavioral changes

# Install as pre-commit hook
intentdiff install-hook
```

**Output:**
```
IntentDiff — Behavioral Change Report
──────────────────────────────────────────────────
✦ Files analyzed      4 changed files (last commit)
✦ Behavioral changes  3 detected  (1 critical, 2 medium)

  ── CRITICAL ──────────────────────────────────────
  auth/validators.py  line 89
  Before: if not user.is_active AND not user.is_banned:
  After:  if not user.is_active OR not user.is_banned:

  ⚠ Logic operator changed AND→OR in security check.
    Before: both conditions must be true to block access.
    After:  either condition alone blocks access. This
            changes who gets blocked — may lock out valid users.

  ── MEDIUM ────────────────────────────────────────
  payment/processor.py  line 134
  Before: if amount <= MAX_SINGLE_TXN:
  After:  if amount < MAX_SINGLE_TXN:

  ⚠ Boundary condition changed <=→<.
    Transactions exactly equal to MAX_SINGLE_TXN
    now fail instead of passing. Edge case regression.

  payment/processor.py  line 201
  Before: except (ValueError, TypeError) as e:
  After:  except Exception as e:

  ⚠ Exception scope widened to bare Exception.
    Now catches errors that should propagate
    (e.g. KeyboardInterrupt via BaseException exclusion gap).

✦ Confidence: 91%
──────────────────────────────────────────────────
Run `intentdiff explain <file>:<line>` for detailed fix suggestion.
```

---

## Tech Stack

- **Language:** Python 3.10+
- **CLI framework:** Typer + Rich
- **AI:** Anthropic Claude API (`claude-sonnet-4-6`) via `anthropic` Python SDK
- **Git integration:** `subprocess` + `git diff`, `git show`
- **GitHub integration:** `gh` CLI for PR diff fetching
- **Packaging:** `pyproject.toml` (hatchling), entry point `intentdiff`
- **Config:** `.intentdiff.toml` in project root or `~/.intentdiff/config.toml`

---

## Project Structure

```
intentdiff/
├── intentdiff/
│   ├── __init__.py
│   ├── cli.py              # Typer app — check, explain, install-hook, config
│   ├── diff_fetcher.py     # Gets diffs from git / staged / PR
│   ├── hunk_parser.py      # Parses unified diff into before/after code hunks
│   ├── analyzer.py         # Sends hunks to Claude, returns BehaviorChange list
│   ├── risk_scorer.py      # Categorizes changes as critical/medium/low risk
│   ├── explainer.py        # Deep-dives one specific change with Claude
│   ├── display.py          # Rich terminal output
│   └── config.py           # Config file reader/writer
├── tests/
│   ├── test_diff_fetcher.py
│   ├── test_hunk_parser.py
│   ├── test_analyzer.py
│   ├── test_risk_scorer.py
│   └── fixtures/
│       ├── logic_operator_change.patch    # AND→OR security check
│       ├── boundary_condition_change.patch # <=→< in payment check
│       ├── exception_scope_change.patch    # ValueError→Exception widening
│       └── safe_refactor.patch            # Refactor with no behavior change (true negative)
├── .github/
│   └── workflows/
│       └── ci.yml
├── pyproject.toml
└── README.md
```

---

## Detailed Module Specs

### `cli.py` — Entry point
```python
app = typer.Typer(name="intentdiff", help="Detect silent behavioral changes in AI-generated code")

@app.command()
def check(
    staged: bool = False,
    commit: Optional[str] = None,
    from_ref: Optional[str] = None,
    to_ref: Optional[str] = None,
    pr: Optional[int] = None,
    risk: str = "medium",   # low | medium | high
):
    """Analyze diff for unintended behavioral changes."""

@app.command()
def explain(location: str):
    """Deep-dive explanation of one behavioral change (file:line)."""

@app.command()
def install_hook():
    """Install as git pre-commit hook."""

@app.command()
def config(api_key: str):
    """Set Anthropic API key."""
```

### `diff_fetcher.py` — Diff retrieval
- `git diff HEAD` → last commit
- `git diff --cached` → staged changes
- `git show <commit>` → specific commit
- `git diff <from>..<to>` → range
- `gh pr diff <number>` → GitHub PR
Return raw unified diff string.

### `hunk_parser.py` — Diff parsing
Parse unified diff into list of `Hunk` dataclasses:
```python
@dataclass
class Hunk:
    file: str
    line_before: int
    line_after: int
    before_lines: str    # Original code block (context + removed lines)
    after_lines: str     # New code block (context + added lines)
    function_context: str  # Name of enclosing function if detectable
```

Key requirement: extract enough context lines (±10) around each change so Claude understands the surrounding logic, not just the changed line.

### `analyzer.py` — Claude API integration
For each hunk, send to Claude with this prompt structure:

```
You are a code behavior analyst. Compare these two code blocks and determine if the behavior changed in a way the developer may NOT have intended.

## Before (original code)
{before_code}

## After (AI-generated change)
{after_code}

## Context
Function: {function_name}
File: {filename}

Look specifically for:
1. Logic operator changes (and/or/not, &&/||)
2. Boundary conditions (< vs <=, > vs >=, == vs !=)
3. Exception handling changes (narrowing or widening except clauses)
4. Null/None guard removal
5. Return value changes (implicit None vs explicit return)
6. Loop condition changes
7. Default parameter changes
8. Type coercion changes

Respond with ONLY valid JSON:
{
  "has_behavioral_change": true,
  "changes": [
    {
      "type": "logic_operator",
      "severity": "critical",
      "before_behavior": "Both conditions required to block access",
      "after_behavior": "Either condition alone blocks access",
      "explanation": "AND changed to OR in security check",
      "line": 89
    }
  ],
  "confidence": 91,
  "false_positive_risk": "low"
}

If no behavioral change: {"has_behavioral_change": false, "changes": [], "confidence": 95}
```

Return list of `BehaviorChange` dataclasses.

### `risk_scorer.py` — Risk categorization
```python
CRITICAL = ["logic_operator", "null_guard_removed", "security_check"]
MEDIUM = ["boundary_condition", "exception_scope", "return_value"]
LOW = ["default_parameter", "type_coercion", "loop_condition"]
```

Filter changes based on `--risk` flag:
- `high` → show only CRITICAL
- `medium` → show CRITICAL + MEDIUM (default)
- `low` → show all

### `display.py` — Rich output
- Group changes by severity (CRITICAL first, red; MEDIUM orange; LOW yellow)
- Show before/after code with syntax highlighting using Rich's `Syntax`
- Show Claude's explanation in plain English
- Confidence score at bottom

---

## The Claude Prompt Engineering Notes

**Critical:** The prompt must instruct Claude to only flag changes that are *unintentional* behavioral shifts, not deliberate improvements. Claude should NOT flag:
- Adding error handling that wasn't there before (that's intentional improvement)
- Fixing a bug (the changed behavior IS the point)
- Refactoring that preserves exact behavior

Claude SHOULD flag:
- Security checks that got weaker
- Error cases that now pass silently
- Boundary conditions that shifted by 1
- Exceptions that got swallowed

---

## README Spec

### Structure:
1. **Hero** — badges + one-liner: *"git diff shows what changed. IntentDiff shows what broke."*
2. **The problem** — concrete example: AI changes `and` to `or` in an auth check. Tests pass. Production fails for 10% of users.
3. **Demo** — `<!-- Add demo.gif here -->`
4. **Install** — `pip install intentdiff`
5. **Quick start** — 3 commands
6. **Sample output** — exact Rich-formatted output from above
7. **How it works** — 3-step: fetch diff → parse hunks → Claude semantic analysis
8. **Risk levels** — explain low/medium/high threshold
9. **Pre-commit integration** — `intentdiff install-hook`
10. **CI integration** — GitHub Actions example
11. **What it detects** — table: logic operators, boundary conditions, exception scope, null guards, return values
12. **What it doesn't flag** — intentional improvements, bug fixes
13. **Contributing**
14. **License — MIT**

---

## CI (`ci.yml`)

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: pytest tests/ -v --cov=intentdiff --cov-fail-under=40
      - run: ruff check intentdiff/
      - run: ruff format --check intentdiff/
```

---

## `pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "intentdiff"
version = "0.1.0"
description = "Detect when AI-generated code silently changes behavior, not just text"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [{name = "UA9-TA", email = "vkrmsatsangi@gmail.com"}]
keywords = ["ai", "git", "diff", "code-review", "developer-tools", "cli", "llm"]
dependencies = [
    "typer>=0.12",
    "rich>=13",
    "anthropic>=0.25",
    "tomli>=2.0; python_version < '3.11'",
]

[project.optional-dependencies]
dev = ["pytest", "ruff", "pytest-mock", "pytest-cov"]

[project.scripts]
intentdiff = "intentdiff.cli:app"

[project.urls]
Homepage = "https://github.com/UA9-TA/intentdiff"
Repository = "https://github.com/UA9-TA/intentdiff"
Changelog = "https://github.com/UA9-TA/intentdiff/blob/main/CHANGELOG.md"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--ignore=tests/fixtures"

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "W", "I"]
ignore = ["E501"]
```

---

## Fixtures (must be real, working examples)

### `tests/fixtures/logic_operator_change.patch`
Unified diff showing `and` → `or` change in an auth check. Must be valid `.patch` format that `git apply` can consume.

### `tests/fixtures/boundary_condition_change.patch`
Unified diff showing `<=` → `<` in a payment amount check.

### `tests/fixtures/exception_scope_change.patch`
Unified diff showing `except (ValueError, TypeError)` → `except Exception`.

### `tests/fixtures/safe_refactor.patch`
Unified diff showing a rename/reformatting with zero behavioral change. IntentDiff must return `has_behavioral_change: false` for this one (true negative test).

---

## What NOT to Build in v1

- No JavaScript/TypeScript support (Python diffs only in v1)
- No web UI
- No automatic PR comments on GitHub
- No team dashboard
- No IDE extension

---

## Definition of Done

- [ ] `intentdiff check` runs on last git commit and detects behavioral changes
- [ ] `intentdiff check --staged` works on staged changes
- [ ] All 3 fixture patches produce correct detections
- [ ] Safe refactor fixture produces zero detections (no false positive)
- [ ] `intentdiff install-hook` writes working pre-commit hook
- [ ] Risk filtering (`--risk low/medium/high`) works correctly
- [ ] Output uses Rich with CRITICAL in red, MEDIUM in orange
- [ ] CI passes on Python 3.10, 3.11, 3.12
- [ ] ruff passes

---

## Repo Details

- GitHub: https://github.com/UA9-TA/intentdiff
- Local path: /Users/chitra/Documents/Projects/intentdiff
- Branch: main
- License: MIT
