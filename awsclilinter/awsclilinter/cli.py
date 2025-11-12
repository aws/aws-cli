import argparse
import difflib
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from awsclilinter.linter import ScriptLinter
from awsclilinter.rules import LintFinding, LintRule
from awsclilinter.rules.base64_rule import Base64BinaryFormatRule
from awsclilinter.rules.pagination_rule import PaginationRule

# ANSI color codes
RED = "\033[31m"
GREEN = "\033[32m"
CYAN = "\033[36m"
RESET = "\033[0m"

# The number of lines to show before an after a fix suggestion, for context within the script
CONTEXT_SIZE = 3


def get_user_choice(prompt: str) -> str:
    """Get user input for interactive mode."""
    while True:
        choice = input(prompt).lower().strip()
        if choice in ["y", "n", "u", "s", "q"]:
            return choice
        print("Invalid choice. Please enter y, n, u, s, or q.")


def display_finding(finding: LintFinding, index: int, total: int, script_content: str):
    """Display a finding to the user with context."""
    src_lines = script_content.splitlines(keepends=True)

    # Apply the edit to get the fixed content
    fixed_content = (
        script_content[: finding.edit.start_pos]
        + finding.edit.inserted_text
        + script_content[finding.edit.end_pos :]
    )
    dest_lines = fixed_content.splitlines(keepends=True)

    start_line = finding.line_start
    end_line = finding.line_end
    context_start = max(0, start_line - CONTEXT_SIZE)
    context_end = min(len(src_lines), end_line + CONTEXT_SIZE + 1)

    src_context = src_lines[context_start:context_end]
    dest_context = dest_lines[context_start:context_end]

    if len(src_context) != len(dest_context):
        raise RuntimeError(
            f"Original and new context lengths must be equal. "
            f"{len(src_context)} != {len(dest_context)}."
        )

    print(f"\n[{index}/{total}] {finding.rule_name}")
    print(f"{finding.description}")

    diff = difflib.unified_diff(src_context, dest_context, lineterm="")
    for line_num, line in enumerate(diff):
        if line_num < 2:
            # First 2 lines are the --- and +++ lines, we don't print those.
            continue
        elif line_num == 2:
            # The 3rd line is the context control line.
            print(f"\n{CYAN}{line}{RESET}")
        elif line.startswith("-"):
            # Removed line
            print(f"{RED}{line}{RESET}", end="")
        elif line.startswith("+"):
            # Added line
            print(f"{GREEN}{line}{RESET}", end="")
        else:
            # Context (unchanged) lines always start with whitespace.
            print(line, end="")


def interactive_mode(
    findings_with_rules: List[Tuple[LintFinding, LintRule]],
    script_content: str,
    linter: ScriptLinter,
) -> Tuple[str, bool]:
    """Run interactive mode with cursor-based workflow.

    Returns:
        Tuple of (modified_script, changes_made)
    """
    current_script = script_content
    # Track the position where we've processed up to for each rule
    cursors: Dict[str, int] = {rule.name: 0 for rule in linter.rules}
    changes_made = False
    i = 0

    while i < len(findings_with_rules):
        finding, rule = findings_with_rules[i]

        # After any script modification, we need fresh findings from the current cursor position
        # because all positions after the modification have shifted
        if changes_made:
            # Get a fresh finding for this rule starting from where we left off
            refreshed = linter.refresh_finding(current_script, rule, cursors[rule.name])
            if refreshed:
                finding = refreshed
                findings_with_rules[i] = (finding, rule)
            else:
                # No more findings for this rule from this position
                i += 1
                continue

        display_finding(finding, i + 1, len(findings_with_rules), current_script)
        choice = get_user_choice(
            "\nApply this fix? [y]es, [n]o, [u]pdate all, [s]ave and exit, [q]uit: "
        )

        if choice == "y":
            # Apply the fix
            current_script = linter.apply_single_fix(current_script, finding)
            # Update cursor to the end of what we just fixed
            cursors[rule.name] = finding.edit.start_pos + len(finding.edit.inserted_text)
            changes_made = True
            i += 1
        elif choice == "n":
            # Skip this fix, move cursor past it
            cursors[rule.name] = finding.edit.end_pos
            i += 1
        elif choice == "u":
            # Accept all remaining findings
            for j in range(i, len(findings_with_rules)):
                f, r = findings_with_rules[j]
                # Refresh if we've made changes
                if changes_made:
                    f = linter.refresh_finding(current_script, r, cursors[r.name])
                    if not f:
                        continue
                current_script = linter.apply_single_fix(current_script, f)
                cursors[r.name] = f.edit.start_pos + len(f.edit.inserted_text)
                changes_made = True
            break
        elif choice == "s":
            break
        elif choice == "q":
            print("Quit without saving.")
            sys.exit(0)

    return current_script, changes_made


def main():
    """Main entry point for the CLI tool."""
    parser = argparse.ArgumentParser(
        description="Lint and upgrade bash scripts from AWS CLI v1 to v2"
    )
    parser.add_argument("--script", required=True, help="Path to the bash script to lint")
    parser.add_argument(
        "--fix", action="store_true", help="Apply fixes to the script (modifies in place)"
    )
    parser.add_argument("--output", help="Output path for the fixed script")
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Interactive mode to review each change",
    )

    args = parser.parse_args()

    if args.fix and args.output:
        print("Error: Cannot use both --fix and --output")
        sys.exit(1)

    if args.fix and args.interactive:
        print("Error: Cannot use both --fix and --interactive")
        sys.exit(1)

    script_path = Path(args.script)
    if not script_path.exists():
        print(f"Error: Script not found: {args.script}")
        sys.exit(1)

    script_content = script_path.read_text()

    rules = [Base64BinaryFormatRule(), PaginationRule()]
    linter = ScriptLinter(rules)
    findings_with_rules = linter.lint(script_content)

    if not findings_with_rules:
        print("No issues found.")
        return

    if args.interactive:
        fixed_content, changes_made = interactive_mode(findings_with_rules, script_content, linter)
        if not changes_made:
            print("No changes accepted.")
            return
        output_path = Path(args.output) if args.output else script_path
        output_path.write_text(fixed_content)
        print(f"Fixed script written to: {output_path}")
    elif args.fix or args.output:
        # Auto-accept all findings
        current_script = script_content
        cursors: Dict[str, int] = {rule.name: 0 for rule in linter.rules}
        changes_made = False

        for i, (finding, rule) in enumerate(findings_with_rules):
            # Refresh if we've made changes
            if changes_made:
                finding = linter.refresh_finding(current_script, rule, cursors[rule.name])
                if not finding:
                    continue

            current_script = linter.apply_single_fix(current_script, finding)
            cursors[rule.name] = finding.edit.start_pos + len(finding.edit.inserted_text)
            changes_made = True

        output_path = Path(args.output) if args.output else script_path
        output_path.write_text(current_script)
        print(f"Fixed script written to: {output_path}")
    else:
        print(f"\nFound {len(findings_with_rules)} issue(s):\n")
        for i, (finding, _) in enumerate(findings_with_rules, 1):
            display_finding(finding, i, len(findings_with_rules), script_content)
        print("\n\nRun with --fix to apply changes or --interactive to review each change.")


if __name__ == "__main__":
    main()
