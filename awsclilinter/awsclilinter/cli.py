import argparse
import sys
from pathlib import Path
from typing import List

from awsclilinter.linter import ScriptLinter
from awsclilinter.rules.base64_rule import Base64BinaryFormatRule
from awsclilinter.rules_base import LintFinding


def get_user_choice(prompt: str) -> str:
    """Get user input for interactive mode."""
    while True:
        choice = input(prompt).lower().strip()
        if choice in ["y", "n", "u", "x"]:
            return choice
        print("Invalid choice. Please enter y, n, u, or x.")


def display_finding(finding: LintFinding, index: int, total: int):
    """Display a finding to the user."""
    print(f"\n[{index}/{total}] {finding.rule_name}")
    print(f"Lines {finding.line_start}-{finding.line_end}: {finding.description}")
    print(f"\nOriginal:\n  {finding.original_text}")
    print(f"\nSuggested:\n  {finding.suggested_fix}")


def interactive_mode(findings: List[LintFinding]) -> List[LintFinding]:
    """Run interactive mode and return accepted findings."""
    accepted = []
    for i, finding in enumerate(findings, 1):
        display_finding(finding, i, len(findings))
        choice = get_user_choice("\nApply this fix? [y]es, [n]o, [u]pdate all, [x] cancel: ")

        if choice == "y":
            accepted.append(finding)
        elif choice == "u":
            accepted.extend(findings[i - 1 :])
            break
        elif choice == "x":
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
        findings = interactive_mode(findings)
        if not findings:
            print("No changes accepted.")
            return

    if args.fix or args.output:
        fixed_content = linter.apply_fixes(script_content, findings)
        output_path = Path(args.output) if args.output else script_path
        output_path.write_text(fixed_content)
        print(f"Fixed script written to: {output_path}")
    else:
        print(f"\nFound {len(findings)} issue(s):\n")
        for i, finding in enumerate(findings, 1):
            display_finding(finding, i, len(findings))
        print("\n\nRun with --fix to apply changes or --interactive to review each change.")


if __name__ == "__main__":
    main()
