import argparse
import difflib
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ast_grep_py.ast_grep_py import SgRoot

from awsclilinter import linter
from awsclilinter.linter import parse
from awsclilinter.rules import LintFinding, LintRule
from awsclilinter.rules.binary_params_base64 import Base64BinaryFormatRule
from awsclilinter.rules.default_pager import DefaultPagerRule
from awsclilinter.rules.deploy_empty_changeset import DeployEmptyChangesetRule
from awsclilinter.rules.ecr_get_login import EcrGetLoginRule
from awsclilinter.rules.hidden_aliases import create_all_hidden_alias_rules
from awsclilinter.rules.s3_copies import S3CopyRule

# ANSI color codes
RED = "\033[31m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RESET = "\033[0m"

# The number of lines to show before an after a fix suggestion, for context within the script
CONTEXT_SIZE = 3


def prompt_user_choice_interactive_mode(auto_fixable: bool = True) -> str:
    """Get user input for interactive mode."""
    while True:
        if auto_fixable:
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
        else:
            choice = input("\n[n] next, [s] save, [q] quit: ").lower().strip()
            if choice in ["n", "s", "q"]:
                return choice
            print("Invalid choice. Please enter n, s, or q.")


def display_finding(finding: LintFinding, index: int, script_content: str):
    """Display a finding to the user with context."""
    if finding.auto_fixable:
        # Apply the edit to get the fixed content
        fixed_content = (
            script_content[: finding.edit.start_pos]
            + finding.edit.inserted_text
            + script_content[finding.edit.end_pos :]
        )

        print(f"\n[{index}] {finding.rule_name}")
        print(f"{finding.description}")

        diff = difflib.unified_diff(
            script_content.splitlines(),
            fixed_content.splitlines(),
            n=CONTEXT_SIZE,
            lineterm=""
        )
        for line_num, line in enumerate(diff):
            if line_num < 2:
                # First 2 lines are the --- and +++ lines, we don't print those.
                continue
            elif line_num == 2:
                # The 3rd line is the context control line.
                print(f"\n{CYAN}{line}{RESET}")
            elif line.startswith("-"):
                # Removed line
                print(f"{RED}{line}{RESET}")
            elif line.startswith("+"):
                # Added line
                print(f"{GREEN}{line}{RESET}")
            else:
                # Context (unchanged) lines always start with whitespace.
                print(line)
    else:
        # Non-fixable issue - show only the problematic lines
        src_lines = script_content.splitlines()
        start_line = finding.line_start
        end_line = finding.line_end
        context_start = max(0, start_line - CONTEXT_SIZE)
        context_end = min(len(src_lines), end_line + CONTEXT_SIZE + 1)

        print(f"\n[{index}] {finding.rule_name} {YELLOW}[MANUAL REVIEW REQUIRED]{RESET}")
        print(f"{finding.description}")

        print(f"\n{CYAN}Lines {context_start + 1}-{context_end + 1}{RESET}")
        for i in range(context_start, context_end):
            line = src_lines[i]
            if start_line <= i <= end_line:
                print(f"{YELLOW}{line}{RESET}")
            else:
                print(f"{line}")

        print(
            f"\n{YELLOW}⚠️  This issue requires manual intervention. "
            f"Suggested action: {finding.suggested_manual_fix}{RESET}"
        )


def apply_all_fixes(
    findings_with_rules: List[Tuple[LintFinding, LintRule]],
    ast: SgRoot,
) -> str:
    """Apply all fixes using rule-by-rule processing.

    Since multiple rules can target the same command, we must process one rule
    at a time and reparse the updated script between rules to get fresh Edit objects.

    Args:
        findings_with_rules: List of findings and their rules.
        ast: Current script represented as an AST.

    Returns:
        Modified script content
    """
    current_ast = ast

    # Group fixable findings by rule
    findings_by_rule: Dict[str, List[LintFinding]] = {}
    for finding, rule in findings_with_rules:
        if finding.auto_fixable:
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

        if not finding.auto_fixable:
            # Non-fixable finding - only allow next, save, or quit
            last_choice = prompt_user_choice_interactive_mode(auto_fixable=False)
            if last_choice == "q":
                print("Quit without saving.")
                sys.exit(0)
            elif last_choice == "s":
                # Save and exit - apply accepted findings before returning
                if accepted_findings:
                    ast = parse(linter.apply_fixes(ast, accepted_findings))
                return ast, len(accepted_findings) > 0, last_choice
            # 'n' means continue to next finding
            continue

        last_choice = prompt_user_choice_interactive_mode(auto_fixable=True)

        if last_choice == "y":
            accepted_findings.append(finding)
        elif last_choice == "n":
            pass  # Skip this finding
        elif last_choice == "u":
            # Accept this and all remaining fixable findings for this rule.
            accepted_findings.append(finding)
            for remaining_finding in findings[i + 1:]:
                if remaining_finding.auto_fixable:
                    accepted_findings.append(remaining_finding)
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

    rules = [
        Base64BinaryFormatRule(),
        DefaultPagerRule(),
        S3CopyRule(),
        DeployEmptyChangesetRule(),
        EcrGetLoginRule(),
        *create_all_hidden_alias_rules(),
        # Rules that do not automatically generate fixes go last
        EcrGetLoginRule(),
    ]

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

        fixable = [(f, r) for f, r in findings_with_rules if f.auto_fixable]
        non_fixable = [(f, r) for f, r in findings_with_rules if not f.auto_fixable]

        if fixable:
            updated_script = apply_all_fixes(fixable, current_ast)
            output_path = Path(args.output) if args.output else script_path
            output_path.write_text(updated_script)
            print(f"Modified script written to: {output_path}")
            print(f"Applied {len(fixable)} fix(es) automatically.")
        else:
            print("No automatic fixes available.")

        if non_fixable:
            print(f"\n{YELLOW}⚠️  {len(non_fixable)} issue(s) require manual review:{RESET}\n")
            for i, (finding, _) in enumerate(non_fixable, 1):
                display_finding(finding, i, script_content)
    else:
        current_ast = parse(script_content)
        findings_with_rules = linter.lint(current_ast, rules)

        if not findings_with_rules:
            print("No issues found.")
            return

        fixable = [(f, r) for f, r in findings_with_rules if f.auto_fixable]
        non_fixable = [(f, r) for f, r in findings_with_rules if not f.auto_fixable]

        print(f"\nFound {len(findings_with_rules)} issue(s):")
        if fixable and non_fixable:
            print(f"  - {len(fixable)} can be automatically fixed")
            print(f"  - {len(non_fixable)} require manual review")
        print()

        for i, (finding, _) in enumerate(findings_with_rules, 1):
            display_finding(finding, i, script_content)

        if fixable:
            print("\n\nRun with --fix to apply automatic fixes")
            if non_fixable:
                print("Non-fixable issues will be shown for manual review")
        else:
            print("\n\nAll issues require manual review")


if __name__ == "__main__":
    main()
