import argparse
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


def get_user_choice(prompt: str) -> str:
    """Get user input for interactive mode."""
    while True:
        choice = input(prompt).lower().strip()
        if choice in ["y", "n", "u", "q"]:
            return choice
        print("Invalid choice. Please enter y, n, u, or q.")


def display_finding(finding: LintFinding, index: int, total: int, script_content: str):
    """Display a finding to the user with context."""
    lines = script_content.splitlines()
    dest_lines = finding.edit.inserted_text.splitlines()
    start_line = finding.line_start
    end_line = finding.line_end
    src_lines_removed = end_line - start_line + 1
    new_lines_added = len(dest_lines)

    # Create a map from line numbers to their indices within the full script file
    line_positions = []
    pos = 0
    for i, line in enumerate(lines):
        line_positions.append((pos, pos + len(line)))
        pos += len(line) + 1

    # Get context lines (3 before and 3 after)
    context_start = max(0, start_line - 3)
    context_end = min(len(lines), end_line + 4)
    src_context_size = context_end - context_start
    dest_context_size = src_context_size + (new_lines_added - src_lines_removed)

    print(f"\n[{index}/{total}] {finding.rule_name}")
    print(f"{finding.description}")
    print(
        f"\n{CYAN}@@ -{context_start + 1},{src_context_size} "
        f"+{context_start + 1},{dest_context_size} @@{RESET}"
    )

    for i in range(context_start, context_end):
        line = lines[i] if i < len(lines) else ""

        if start_line <= i <= end_line:
            # This line is actually being modified
            print(f"{RED}-{line}{RESET}")

            if i == end_line:
                line_start_pos, _ = line_positions[i]
                start_pos_in_line = max(0, finding.edit.start_pos - line_start_pos)
                end_pos_in_line = min(len(line), finding.edit.end_pos - line_start_pos)
                new_line = line[:start_pos_in_line] + finding.suggested_fix + line[end_pos_in_line:]
                # Print the new line suggestion. The line number will always be the start line
                # returned by ast-grep.
                print(f"{GREEN}+{new_line}{RESET}")
        else:
            # Context line
            print(f"{line}")


def interactive_mode(findings: List[LintFinding], script_content: str) -> List[LintFinding]:
    """Run interactive mode and return accepted findings."""
    accepted = []
    for i, finding in enumerate(findings, 1):
        display_finding(finding, i, len(findings), script_content)
        choice = get_user_choice("\nApply this fix? [y]es, [n]o, [u]pdate all, [q]uit: ")

        if choice == "y":
            accepted.append(finding)
        elif choice == "u":
            accepted.extend(findings[i - 1 :])
            break
        elif choice == "q":
            print("Cancelled.")
            sys.exit(0)

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
