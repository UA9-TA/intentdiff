# IntentDiff — IntentDiff v1.0

![IntentDiff](https://img.shields.io/badge/IntentDiff-v0.1.0-blue)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow)

*git diff shows what changed. IntentDiff shows what broke.*

## What You Are Building

**IntentDiff** is an open-source CLI tool that uses Claude AI to semantically analyze git diffs and detect when AI-generated code has silently changed the *intent* or *behavior* of your codebase — not just the text.

The core problem: A standard `git diff` shows what changed in text. It cannot tell you that the AI swapped `and` for `or` in a security check, removed a null guard that was load-bearing, changed a `<=` to `<` in a rate limiter, or dropped an exception handler without replacing it. These changes pass syntax checks, linters, and sometimes even tests — they only fail in production.

IntentDiff reads the diff, understands what the original code *did*, understands what the new code *does*, and flags every place where the behavior changed in a way the developer may not have intended.

## Concrete Example

AI changes `and` to `or` in an auth check. Tests pass. Production fails for 10% of users.

```python
# Before
if not user.is_active and not user.is_banned:

# After
if not user.is_active or not user.is_banned:
```

## Install

```bash
pip install intentdiff
```

## Quick Start

```bash
# Analyze the last commit
intentdiff check

# Analyze staged changes before committing
intentdiff check --staged

# Analyze a specific commit or range
intentdiff check --commit abc1234
```

## Sample Output

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

## How It Works

1. **Fetch diff**: IntentDiff uses standard git commands to fetch the diff (staged, last commit, specific commit, or PR).
2. **Parse hunks**: It extracts the unified diff hunks, providing enough context lines (±10) around the changes.
3. **Claude semantic analysis**: Each hunk is sent to Claude, which acts as a code behavior analyst to determine if the *intent* or *behavior* of the code has changed unintentionally.

## Risk Levels

You can set a risk threshold for what gets flagged using `--risk` flag.

- `low`: flags everything
- `medium`: flags critical and medium changes (default)
- `high`: only flags critical behavioral changes

```bash
intentdiff check --risk high
```

## Pre-commit Integration

Install IntentDiff as a pre-commit hook to catch behavioral changes before they are committed.

```bash
intentdiff install-hook
```

## CI Integration

Add this to your `.github/workflows/ci.yml` to run IntentDiff on pull requests.

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - run: pip install intentdiff
      - run: intentdiff check
```

## What It Detects

| Type | Examples |
| --- | --- |
| **Logic operator changes** | `and`/`or`/`not`, `&&`/`\|\|` |
| **Boundary conditions** | `<` vs `<=`, `>` vs `>=`, `==` vs `!=` |
| **Exception handling changes** | Narrowing or widening `except` clauses |
| **Null/None guard removal** | Removing checks for `None` or `null` |
| **Return value changes** | Implicit `None` vs explicit return |
| **Loop condition changes** | Changing `range(1, n)` to `range(0, n)` |
| **Default parameter changes** | Changing `timeout=5` to `timeout=10` |
| **Type coercion changes** | Implicitly casting to a different type |

## What It Doesn't Flag

- Intentional improvements
- Bug fixes
- Safe refactoring that preserves the exact behavior

## Contributing

We welcome contributions! Please open an issue or submit a pull request on GitHub.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
