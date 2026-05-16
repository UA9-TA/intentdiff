import json
from dataclasses import dataclass
from typing import List, Optional

import anthropic

from intentdiff.config import get_api_key
from intentdiff.hunk_parser import Hunk


@dataclass
class BehaviorChange:
    file: str
    type: str
    severity: str
    before_behavior: str
    after_behavior: str
    explanation: str
    line: int
    before_code: str
    after_code: str
    confidence: int


@dataclass
class AnalysisResult:
    has_behavioral_change: bool
    changes: List[BehaviorChange]
    confidence: int
    false_positive_risk: str


def analyze_hunks(hunks: List[Hunk]) -> List[AnalysisResult]:
    api_key = get_api_key()
    if not api_key:
        raise ValueError(
            "Anthropic API key not found. Please set ANTHROPIC_API_KEY environment variable or run 'intentdiff config <key>'"
        )

    client = anthropic.Anthropic(api_key=api_key)
    results = []

    for hunk in hunks:
        result = _analyze_hunk(client, hunk)
        if result:
            results.append(result)

    return results


def _analyze_hunk(client: anthropic.Anthropic, hunk: Hunk) -> Optional[AnalysisResult]:
    prompt = f"""You are a code behavior analyst. Compare these two code blocks and determine if the behavior changed in a way the developer may NOT have intended.

## Before (original code)
```python
{hunk.before_lines}
```

## After (AI-generated change)
```python
{hunk.after_lines}
```

## Context
Function: {hunk.function_context}
File: {hunk.file}

Look specifically for:
1. Logic operator changes (and/or/not, &&/||)
2. Boundary conditions (< vs <=, > vs >=, == vs !=)
3. Exception handling changes (narrowing or widening except clauses)
4. Null/None guard removal
5. Return value changes (implicit None vs explicit return)
6. Loop condition changes
7. Default parameter changes
8. Type coercion changes

Respond with ONLY valid JSON matching this schema:
{{
  "has_behavioral_change": true,
  "changes": [
    {{
      "type": "logic_operator",
      "severity": "critical",
      "before_behavior": "Both conditions required to block access",
      "after_behavior": "Either condition alone blocks access",
      "explanation": "AND changed to OR in security check",
      "line": 89
    }}
  ],
  "confidence": 91,
  "false_positive_risk": "low"
}}

If no behavioral change, or if it is a safe refactor, or an intentional improvement/bugfix: {{"has_behavioral_change": false, "changes": [], "confidence": 95}}
"""

    try:
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1024,
            temperature=0,
            system="You are an expert code reviewer. You respond ONLY with valid JSON.",
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.content[0].text

        # Clean up the response in case Claude adds markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]

        data = json.loads(content.strip())

        if not data.get("has_behavioral_change"):
            return AnalysisResult(False, [], data.get("confidence", 100), "low")

        changes = []
        for c in data.get("changes", []):
            changes.append(
                BehaviorChange(
                    file=hunk.file,
                    type=c.get("type", "unknown"),
                    severity=c.get("severity", "medium"),
                    before_behavior=c.get("before_behavior", ""),
                    after_behavior=c.get("after_behavior", ""),
                    explanation=c.get("explanation", ""),
                    line=c.get("line", hunk.line_after),
                    before_code=hunk.before_lines,
                    after_code=hunk.after_lines,
                    confidence=data.get("confidence", 90),
                )
            )

        return AnalysisResult(
            has_behavioral_change=data.get("has_behavioral_change", False),
            changes=changes,
            confidence=data.get("confidence", 90),
            false_positive_risk=data.get("false_positive_risk", "low"),
        )

    except Exception as e:
        # Silently fail for individual hunks if API fails, or we could log it
        print(f"Error analyzing hunk in {hunk.file}: {e}")
        return None
