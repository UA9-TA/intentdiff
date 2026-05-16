import re
from dataclasses import dataclass
from typing import List


@dataclass
class Hunk:
    file: str
    line_before: int
    line_after: int
    before_lines: str  # Original code block (context + removed lines)
    after_lines: str  # New code block (context + added lines)
    function_context: str  # Name of enclosing function if detectable


def parse_diff(diff_text: str) -> List[Hunk]:
    """Parse a unified diff into a list of Hunks."""
    if not diff_text:
        return []

    hunks = []
    current_file = None

    # Split the diff into file blocks
    file_blocks = re.split(r"^diff --git ", diff_text, flags=re.MULTILINE)

    for block in file_blocks:
        if not block.strip():
            continue

        lines = block.splitlines()

        # Parse file name
        for line in lines:
            if line.startswith("+++ b/"):
                current_file = line[6:]
                break
            elif line.startswith("+++ "):
                # Handle patches without b/ prefix
                current_file = line[4:]
                break

        if not current_file:
            continue

        # Extract hunks within the file
        hunk_matches = list(
            re.finditer(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*?)$", block, flags=re.MULTILINE)
        )

        for i, match in enumerate(hunk_matches):
            line_before = int(match.group(1))
            line_after = int(match.group(2))
            function_context = match.group(3).strip()

            # Get the content of this hunk
            start_pos = match.end() + 1
            if i + 1 < len(hunk_matches):
                end_pos = hunk_matches[i + 1].start()
            else:
                end_pos = len(block)

            hunk_content = block[start_pos:end_pos]

            before_lines = []
            after_lines = []

            for line in hunk_content.splitlines():
                if line.startswith("\\ No newline"):
                    continue

                if line.startswith("-"):
                    before_lines.append(line[1:])
                elif line.startswith("+"):
                    after_lines.append(line[1:])
                elif line.startswith(" "):
                    before_lines.append(line[1:])
                    after_lines.append(line[1:])
                elif line == "":
                    before_lines.append("")
                    after_lines.append("")

            hunks.append(
                Hunk(
                    file=current_file,
                    line_before=line_before,
                    line_after=line_after,
                    before_lines="\n".join(before_lines),
                    after_lines="\n".join(after_lines),
                    function_context=function_context,
                )
            )

    return hunks
