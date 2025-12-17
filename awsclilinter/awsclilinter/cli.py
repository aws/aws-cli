import argparse
import difflib
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ast_grep_py.ast_grep_py import SgRoot

from awsclilinter import linter
from awsclilinter.linter import parse
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


def prompt_user_choice_interactive_mode() -> str:
    """Get user input for interactive mode."""
    while True:
        choice = (
            input(
                "\nApply this fix? [y] yes, [n] no, [u] update all, [s] save and exit, [q] quit: "
            )
            .lower()
            .strip()
        )
        if choice in ["y", "n", "u", "s", "q"]:
            return choice
        print("Invalid choice. Please enter y, n, u, s, or q.")


def display_finding(finding: LintFinding, index: int, script_content: str):
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

    print(f"\n[{index}] {finding.rule_name}")
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
    ast: SgRoot,
) -> str:
    """Apply all fixes using rule-by-rule processing.

    Since multiple rules can target the same command, we must process one rule
    at a time and re-parse the updated script between rules to get fresh Edit objects.

    Args:
        findings_with_rules: List of findings and their rules.
        ast: Current script represented as an AST.

    Returns:
        Modified script content
    """
    current_ast = ast

    # Group findings by rule
    findings_by_rule: Dict[str, List[LintFinding]] = {}
    for finding, rule in findings_with_rules:
        if rule.name not in findings_by_rule:
            findings_by_rule[rule.name] = []
        findings_by_rule[rule.name].append(finding)

    # Process one rule at a time, re-parsing between rules
    for rule in findings_by_rule:
        updated_script = linter.apply_fixes(current_ast, findings_by_rule[rule])
        current_ast = parse(updated_script)
    return current_ast.root().text()


def interactive_mode_for_rule(
    findings: List[LintFinding],
    ast: SgRoot,
    finding_offset: int,
) -> Tuple[SgRoot, bool, Optional[str]]:
    """Run interactive mode for a single rule's findings.

    Args:
        findings: List of findings for this rule.
        ast: Current script content, represented as an AST.
        finding_offset: Offset for display numbering.

    Returns:
        Tuple of (ast, changes_made, last_choice)
        ast is the resulting AST from this interactive mode execution.
        changes_made whether the AST was updated based on user choice.
        last_choice is the last choice entered by the user.
    """
    accepted_findings: List[LintFinding] = []
    last_choice: Optional[str] = None

    for i, finding in enumerate(findings):
        display_finding(finding, finding_offset + i + 1, ast.root().text())
        last_choice = prompt_user_choice_interactive_mode()

        if last_choice == "y":
            accepted_findings.append(finding)
        elif last_choice == "n":
            pass  # Skip this finding
        elif last_choice == "u":
            # Accept this and all remaining findings for this rule.
            accepted_findings.extend(findings[i:])
            if accepted_findings:
                ast = parse(linter.apply_fixes(ast, accepted_findings))
            return ast, True, last_choice
        elif last_choice == "s":
            # Apply accepted findings and stop processing
            if accepted_findings:
                ast = parse(linter.apply_fixes(ast, accepted_findings))
            return ast, len(accepted_findings) > 0, last_choice
        elif last_choice == "q":
            print("Quitting without saving.")
            sys.exit(0)

    if accepted_findings:
        ast = parse(linter.apply_fixes(ast, accepted_findings))
        return ast, True, last_choice

    return ast, False, last_choice


def main():
    """Main entry point for the CLI tool."""
    parser = argparse.ArgumentParser(
        description="Lint and upgrade bash scripts from AWS CLI v1 to v2"
    )
    parser.add_argument("--script", required=True, help="Path to the bash script to lint")
    parser.add_argument(
        "--fix", action="store_true", help="Apply fixes to the script (modifies in place)"
    )
    parser.add_argument("--output", help="Output path for the modified script")
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

    if args.interactive:
        current_ast = parse(script_content)

        current_script = script_content
        any_changes = False
        finding_offset = 0
        findings_found = 0

        # Process one rule at a time, re-parsing between rules

        for rule_index, rule in enumerate(rules):
            # Lint for this specific rule with current script state
            rule_findings = linter.lint_for_rule(current_ast, rule)

            if not rule_findings:
                continue

            findings_found += len(rule_findings)
            current_ast, changes_made, last_choice = interactive_mode_for_rule(
                rule_findings, current_ast, finding_offset
            )

            if changes_made:
                current_script = current_ast.root().text()
                any_changes = True

            finding_offset += len(rule_findings)

            if last_choice == "s":
                break

            # If user chose 'u', auto-apply all remaining rules
            if last_choice == "u":
                for remaining_rule in rules[rule_index + 1 :]:
                    remaining_findings = linter.lint_for_rule(current_ast, remaining_rule)
                    if remaining_findings:
                        current_script = linter.apply_fixes(current_ast, remaining_findings)
                        any_changes = True
                break

        if findings_found == 0:
            print("No issues found.")
            return
        else:
            print(f"Found {findings_found} issues.")

        if not any_changes:
            print("No changes accepted.")
            return

        output_path = Path(args.output) if args.output else script_path
        output_path.write_text(current_script)
        print(f"Modified script written to: {output_path}")
    elif args.fix or args.output:
        current_ast = parse(script_content)
        findings_with_rules = linter.lint(current_ast, rules)
        updated_script = apply_all_fixes(findings_with_rules, current_ast)
        output_path = Path(args.output) if args.output else script_path
        output_path.write_text(updated_script)
        print(f"Modified script written to: {output_path}")
    else:
        current_ast = parse(script_content)
        findings_with_rules = linter.lint(current_ast, rules)

        if not findings_with_rules:
            print("No issues found.")
            return

        print(f"\nFound {len(findings_with_rules)} issue(s):\n")
        for i, (finding, _) in enumerate(findings_with_rules, 1):
            display_finding(finding, i, script_content)
        print("\n\nRun with --fix to apply changes or --interactive to review each change.")


if __name__ == "__main__":
    main()
