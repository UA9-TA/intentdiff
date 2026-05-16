import anthropic

from intentdiff.config import get_api_key


def explain_change(file: str, line: int) -> str:
    """Deep-dive explanation of one behavioral change (file:line)."""
    # For a real implementation, we would extract the specific hunk for this file:line
    # and send it to Claude for a more detailed explanation.
    # For v1, we'll do a simpler simulation.

    api_key = get_api_key()
    if not api_key:
        raise ValueError(
            "Anthropic API key not found. Please set ANTHROPIC_API_KEY environment variable or run 'intentdiff config <key>'"
        )

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""You are an expert code reviewer explaining a behavioral change.
I need a detailed explanation of what might have gone wrong at {file}:{line}.
Please provide a deep-dive explanation of common silent behavioral changes that can happen in AI-generated code, and how to fix them."""

    try:
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1024,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception as e:
        return f"Error getting explanation from Claude: {e}"
