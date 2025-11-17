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


def apply_all_fixes(
    findings_with_rules: List[Tuple[LintFinding, LintRule]],
    script_content: str,
    linter: ScriptLinter,
) -> str:
    """Apply all fixes using rule-by-rule processing.

    Since multiple rules can target the same command, we must process one rule
    at a time and re-parse between rules to get fresh Edit objects.

    Args:
        findings_with_rules: List of findings and their rules
        script_content: Current script content
        linter: The linter instance

    Returns:
        Modified script content
    """
    current_script = script_content

    # Group findings by rule
    findings_by_rule: Dict[str, List[LintFinding]] = {}
    for finding, rule in findings_with_rules:
        if rule.name not in findings_by_rule:
            findings_by_rule[rule.name] = []
        findings_by_rule[rule.name].append(finding)

    # Process one rule at a time, re-parsing between rules
    for rule in linter.rules:
        if rule.name in findings_by_rule:
            current_script = linter.apply_fixes(current_script, findings_by_rule[rule.name])

    return current_script


def interactive_mode_for_rule(
    findings: List[LintFinding],
    rule: LintRule,
    script_content: str,
    linter: ScriptLinter,
    finding_offset: int,
    total_findings: int,
) -> Tuple[str, bool, bool, bool]:
    """Run interactive mode for a single rule's findings.

    Args:
        findings: List of findings for this rule
        rule: The rule being processed
        script_content: Current script content
        linter: The linter instance
        finding_offset: Offset for display numbering
        total_findings: Total number of findings across all rules

    Returns:
        Tuple of (modified_script, changes_made, should_continue, auto_approve_remaining)
        should_continue is False if user chose 's' (save) or 'q' (quit)
        auto_approve_remaining is True if user chose 'u' (update all)
    """
    accepted_findings: List[LintFinding] = []

    for i, finding in enumerate(findings):
        display_finding(finding, finding_offset + i + 1, total_findings, script_content)
        choice = get_user_choice(
            "\nApply this fix? [y]es, [n]o, [u]pdate all, [s]ave and exit, [q]uit: "
        )

        if choice == "y":
            accepted_findings.append(finding)
        elif choice == "n":
            pass  # Skip this finding
        elif choice == "u":
            # Accept this and all remaining findings for all rules
            accepted_findings.extend(findings[i:])
            if accepted_findings:
                script_content = linter.apply_fixes(script_content, accepted_findings)
            return script_content, True, True, True
        elif choice == "s":
            # Apply accepted findings and stop processing
            if accepted_findings:
                script_content = linter.apply_fixes(script_content, accepted_findings)
            return script_content, len(accepted_findings) > 0, False, False
        elif choice == "q":
            print("Quit without saving.")
            sys.exit(0)

    if accepted_findings:
        script_content = linter.apply_fixes(script_content, accepted_findings)
        return script_content, True, True, False

    return script_content, False, True, False


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
        # Process one rule at a time, re-parsing between rules
        current_script = script_content
        any_changes = False
        finding_offset = 0

        # Calculate total findings for display
        total_findings = len(findings_with_rules)

        for rule_index, rule in enumerate(linter.rules):
            # Lint for this specific rule with current script state
            rule_findings = linter.lint_for_rule(current_script, rule)

            if not rule_findings:
                continue

            current_script, changes_made, should_continue, auto_approve = interactive_mode_for_rule(
                rule_findings, rule, current_script, linter, finding_offset, total_findings
            )

            if changes_made:
                any_changes = True

            finding_offset += len(rule_findings)

            if not should_continue:
                break

            # If user chose 'u', auto-apply all remaining rules
            if auto_approve:
                for remaining_rule in linter.rules[rule_index + 1 :]:
                    remaining_findings = linter.lint_for_rule(current_script, remaining_rule)
                    if remaining_findings:
                        current_script = linter.apply_fixes(current_script, remaining_findings)
                        any_changes = True
                break

        if not any_changes:
            print("No changes accepted.")
            return

        output_path = Path(args.output) if args.output else script_path
        output_path.write_text(current_script)
        print(f"Fixed script written to: {output_path}")
    elif args.fix or args.output:
        fixed_content = apply_all_fixes(findings_with_rules, script_content, linter)
        output_path = Path(args.output) if args.output else script_path
        output_path.write_text(fixed_content)
        print(f"Fixed script written to: {output_path}")
    else:
        print(f"\nFound {len(findings_with_rules)} issue(s):\n")
        for i, (finding, _) in enumerate(findings_with_rules, 1):
            display_finding(finding, i, len(findings_with_rules), script_content)
        print("\n\nRun with --fix to apply changes or --interactive to review each change.")


if __name__ == "__main__":
    main()
