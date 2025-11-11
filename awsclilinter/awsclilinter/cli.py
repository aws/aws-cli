import argparse
import difflib
import sys
from pathlib import Path
from typing import List

from awsclilinter.linter import ScriptLinter
from awsclilinter.rules.base64_rule import Base64BinaryFormatRule
from awsclilinter.rules_base import LintFinding

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
        if choice in ["y", "n", "u", "s"]:
            return choice
        print("Invalid choice. Please enter y, n, u, or s.")


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
            print(f"{RED}{line}{RESET}", end="")
        elif line.startswith("+"):
            print(f"{GREEN}{line}{RESET}", end="")
        else:
            print(line, end="")


def interactive_mode(findings: List[LintFinding], script_content: str) -> List[LintFinding]:
    """Run interactive mode and return accepted findings."""
    accepted = []
    for i, finding in enumerate(findings, 1):
        display_finding(finding, i, len(findings), script_content)
        choice = get_user_choice("\nApply this fix? [y]es, [n]o, [u]pdate all, [s]ave and exit: ")

        if choice == "y":
            accepted.append(finding)
        elif choice == "u":
            accepted.extend(findings[i - 1 :])
            break
        elif choice == "s":
            break

    return accepted


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

    rules = [Base64BinaryFormatRule()]
    linter = ScriptLinter(rules)
    findings = linter.lint(script_content)

    if not findings:
        print("No issues found.")
        return

    if args.interactive:
        findings = interactive_mode(findings, script_content)
        if not findings:
            print("No changes accepted.")
            return

    if args.fix or args.output or args.interactive:
        # Interactive mode is functionally equivalent to --fix, except the user
        # can select a subset of the changes to apply.
        fixed_content = linter.apply_fixes(script_content, findings)
        output_path = Path(args.output) if args.output else script_path
        output_path.write_text(fixed_content)
        print(f"Fixed script written to: {output_path}")
    else:
        print(f"\nFound {len(findings)} issue(s):\n")
        for i, finding in enumerate(findings, 1):
            display_finding(finding, i, len(findings), script_content)
        print("\n\nRun with --fix to apply changes or --interactive to review each change.")


if __name__ == "__main__":
    main()
