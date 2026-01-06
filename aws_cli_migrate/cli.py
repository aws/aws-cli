# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import argparse
import difflib
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from ast_grep_py.ast_grep_py import SgRoot

from aws_cli_migrate import __version__, linter
from aws_cli_migrate.linter import parse
from aws_cli_migrate.rules import LintFinding, LintRule
from aws_cli_migrate.rules.binary_params_base64 import Base64BinaryFormatRule
from aws_cli_migrate.rules.cli_input_json import CLIInputJSONRule
from aws_cli_migrate.rules.default_pager import DefaultPagerRule
from aws_cli_migrate.rules.deploy_empty_changeset import DeployEmptyChangesetRule
from aws_cli_migrate.rules.ecr_get_login import EcrGetLoginRule
from aws_cli_migrate.rules.hidden_aliases import create_all_hidden_alias_rules
from aws_cli_migrate.rules.s3_copies import S3CopyRule

# ANSI color codes
RED = "\033[31m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RESET = "\033[0m"

# The number of lines to show before an after a fix suggestion, for context within the script
CONTEXT_SIZE = 3


def _color_text(text, color_code):
    """Colorize text for terminal output only if a TTY is available."""
    if sys.stdout.isatty():
        return f"{color_code}{text}{RESET}"
    return text


def _prompt_user_choice_interactive_mode(auto_fixable: bool = True) -> str:
    """Get user input for interactive mode."""
    while True:
        if auto_fixable:
            choice = (
                input(
                    "\nApply this fix? [y] yes, [n] no, "
                    "[u] update all, [s] save and exit, [q] quit: "
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


def _summarize_non_fixable_findings(
        non_auto_fixable_findings: List[LintFinding],
        script_content: str
):
    """Summarize the input non-fixable findings."""
    warning_header = _color_text(
        f"⚠️  {len(non_auto_fixable_findings)} issue(s) "
        f"require manual review:",
        YELLOW
    )
    print(f"\n{warning_header}\n")
    for i, finding in enumerate(non_auto_fixable_findings, 1):
        _display_finding(finding, i, script_content)


def _display_finding(finding: LintFinding, index: int, script_content: str):
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
            script_content.splitlines(), fixed_content.splitlines(), n=CONTEXT_SIZE, lineterm=""
        )
        for line_num, line in enumerate(diff):
            if line_num < 2:
                # First 2 lines are the --- and +++ lines, we don't print those.
                continue
            elif line_num == 2:
                # The 3rd line is the context control line.
                print(f"\n{_color_text(line, CYAN)}")
            elif line.startswith("-"):
                # Removed line
                print(_color_text(line, RED))
            elif line.startswith("+"):
                # Added line
                print(_color_text(line, GREEN))
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

        manual_tag = _color_text("[MANUAL REVIEW REQUIRED]", YELLOW)
        print(f"\n[{index}] {finding.rule_name} {manual_tag}")
        print(f"{finding.description}\n")

        print(_color_text(f"Lines {context_start + 1}-{context_end + 1}", CYAN))
        for i in range(context_start, context_end):
            line = src_lines[i]
            if start_line <= i <= end_line:
                print(f"{_color_text(line, YELLOW)}")
            else:
                print(f"{line}")

        warning_msg = _color_text(
            f"⚠️  This issue requires manual intervention. "
            f"Suggested action: {finding.suggested_manual_fix}",
            YELLOW,
        )
        print(f"\n{warning_msg}")


def _lint_and_generate_updated_script(
    rules: List[LintRule],
    script_ast: SgRoot,
) -> tuple[SgRoot, int, list[LintFinding]]:
    current_ast = script_ast
    findings_found = 0
    num_auto_fixable_findings = 0
    non_auto_fixable = []

    for rule_index, rule in enumerate(rules):
        # Lint for this specific rule with current script state
        rule_findings = linter.lint_for_rule(current_ast, rule)
        auto_fixable_findings = [f for f in rule_findings if f.auto_fixable]

        findings_found += len(rule_findings)
        num_auto_fixable_findings += len(auto_fixable_findings)

        non_auto_fixable.extend(
            finding for finding in rule_findings if not finding.auto_fixable
        )

        # Avoid an unnecessary reparse if no changes were made to the script
        if not auto_fixable_findings:
            continue

        current_ast = parse(linter.apply_fixes(current_ast, auto_fixable_findings))
    return current_ast, num_auto_fixable_findings, non_auto_fixable


def auto_fix_mode(
    rules: List[LintRule],
    script_content: str,
    output_path: Path,
):
    """Handler for auto-fix mode. Lints the input script based on the input rules list. If
    any findings were detected that can be automatically fixed, applies the automatic
    fixes to the script and writes it to the output path.

    Args:
        rules: List of linting rules to run against the input script.
        script_content: Current script represented as an AST.
        output_path: The path to write the updated script if any findings were detected.
    """
    current_ast, num_auto_fixable_findings, non_auto_fixable = _lint_and_generate_updated_script(
        rules, parse(script_content)
    )

    if not non_auto_fixable and not num_auto_fixable_findings:
        print("No issues found.")
        return

    # If there were findings detected, display the number of findings.
    print(f"Found {num_auto_fixable_findings + len(non_auto_fixable)} issue(s).")

    # If there were findings that need manual review, summarize them.
    if non_auto_fixable:
        _summarize_non_fixable_findings(
            non_auto_fixable,
            script_content
        )

    # Summarize the auto-fix results last.
    if num_auto_fixable_findings:
        output_path.write_text(current_ast.root().text())
        print(f"Modified script written to: {output_path}")
        print(f"Applied {num_auto_fixable_findings} fix(es) automatically.")
    else:
        print("No findings with automatic fixes were detected. No script updates were written.")


def dry_run_mode(
    rules: List[LintRule],
    script_content: str,
    script_path: Path,
):
    """Handler for dry-run mode. Lints the input script based on the input rules list and
    prints the diff to stdout.

    Args:
        rules: List of linting rules to run against the input script.
        script_content: The input script.
        script_path: Path to the script being linted.
    """
    current_ast, num_auto_fixable_findings, non_auto_fixable = _lint_and_generate_updated_script(
        rules, parse(script_content)
    )

    if not num_auto_fixable_findings and not non_auto_fixable:
        print("No issues found.")
        return

    diff = difflib.unified_diff(
        script_content.splitlines(),
        current_ast.root().text().splitlines(),
        n=CONTEXT_SIZE,
        lineterm="",
    )
    for line_num, line in enumerate(diff):
        if line_num == 0:
            # First line is always '--- '
            print(f"{line}{script_path}")
        elif line_num == 1:
            # Second line is always '+++ '
            print(f"{line}{script_path}")
        elif line.startswith("@"):
            # Context control line.
            print(f"\n{_color_text(line, CYAN)}")
        elif line.startswith("-"):
            # Removed line
            print(_color_text(line, RED))
        elif line.startswith("+"):
            # Added line
            print(_color_text(line, GREEN))
        else:
            # Context (unchanged) lines always start with whitespace.
            print(line)

    if non_auto_fixable:
        _summarize_non_fixable_findings(
            non_auto_fixable,
            script_content
        )

    print(f"\nFound {num_auto_fixable_findings + len(non_auto_fixable)} issue(s):")
    if num_auto_fixable_findings and non_auto_fixable:
        print(f"  - {num_auto_fixable_findings} can be automatically fixed")
        print(f"  - {len(non_auto_fixable)} require manual review")

    if num_auto_fixable_findings:
        print(
            "\n\nRun with `--fix` to apply automatic fixes to the script, "
            "or `--output PATH` to write the modified script to a specific path."
        )
    else:
        print("\n\nAll issues require manual review.")


def interactive_mode(
    rules: List[LintRule],
    script_content: str,
    output_path: Path,
):
    """Handler for interactive mode. Lints the input script based on the input rules list and
    interactively prompts the user to address each fix.

    Args:
        rules: List of linting rules to run against the input script.
        script_content: The input script.
        output_path: Path to the script being linted.
    """
    current_ast = parse(script_content)

    current_script = script_content
    finding_offset = 0
    findings_found = 0
    num_auto_fixes_applied = 0
    non_auto_fixable_findings_to_summarize: List[LintFinding] = []

    # Process one rule at a time, reparsing between rules
    for rule_index, rule in enumerate(rules):
        # Lint for this specific rule with current script state
        rule_findings = linter.lint_for_rule(current_ast, rule)

        if not rule_findings:
            continue

        findings_found += len(rule_findings)
        current_ast, num_fixes_applied, last_choice = interactive_mode_for_rule(
            rule_findings, current_ast, finding_offset
        )

        if num_fixes_applied > 0:
            current_script = current_ast.root().text()
            num_auto_fixes_applied += num_fixes_applied

        finding_offset += len(rule_findings)

        if last_choice == "s":
            break

        # If user chose 'u', auto-apply all remaining rules
        if last_choice == "u":
            # TODO check if we can use recursion or reuse the outer function rather than rewriting most of the
            # outer function here.
            for remaining_rule in rules[rule_index + 1:]:
                findings_for_remaining_rule = linter.lint_for_rule(current_ast, remaining_rule)

                if not findings_for_remaining_rule:
                    continue

                findings_found += len(findings_for_remaining_rule)

                if not remaining_rule.auto_fixable:
                    non_auto_fixable_findings_to_summarize.extend(findings_for_remaining_rule)
                    continue

                current_ast = parse(linter.apply_fixes(current_ast, findings_for_remaining_rule))
                current_script = current_ast.root().text()
                num_auto_fixes_applied += num_fixes_applied
            break

    if findings_found == 0:
        print("No issues found.")
        return
    else:
        print(f"Found {findings_found} issue(s).")
        if non_auto_fixable_findings_to_summarize:
            _summarize_non_fixable_findings(
                non_auto_fixable_findings_to_summarize,
                script_content
            )

    if num_auto_fixes_applied:
        output_path.write_text(current_script)
        print(f"Modified script written to: {output_path}")
        print(f"Applied {num_auto_fixes_applied} fix(es) automatically.")
    else:
        print("No changes were accepted. No script updates were written.")


def interactive_mode_for_rule(
    findings: List[LintFinding],
    ast: SgRoot,
    finding_offset: int,
) -> Tuple[SgRoot, int, Optional[str]]:
    """Run interactive mode for a single rule's findings.

    Args:
        findings: List of findings for this rule.
        ast: Current script content, represented as an AST.
        finding_offset: Offset for display numbering.

    Returns:
        Tuple of (ast, applied_fixes, last_choice)
        ast is the resulting AST from this interactive mode execution.
        applied_fixes number of fixes applied to the AST.
        last_choice is the last choice entered by the user.
    """
    accepted_findings: List[LintFinding] = []
    last_choice: Optional[str] = None

    for i, finding in enumerate(findings):
        _display_finding(finding, finding_offset + i + 1, ast.root().text())

        if not finding.auto_fixable:
            # Non-fixable finding - only allow next, save, or quit
            last_choice = _prompt_user_choice_interactive_mode(auto_fixable=False)
            if last_choice == "q":
                print("Quit without saving.")
                sys.exit(0)
            elif last_choice == "s":
                # Save and exit - apply accepted findings before returning
                if accepted_findings:
                    ast = parse(linter.apply_fixes(ast, accepted_findings))
                return ast, len(accepted_findings), last_choice
            # 'n' means continue to next finding
            continue

        last_choice = _prompt_user_choice_interactive_mode(auto_fixable=True)

        if last_choice == "y":
            accepted_findings.append(finding)
        elif last_choice == "n":
            pass  # Skip this finding
        elif last_choice == "u":
            # Accept this and all remaining fixable findings for this rule.
            accepted_findings.append(finding)
            for remaining_finding in findings[i + 1 :]:
                if remaining_finding.auto_fixable:
                    accepted_findings.append(remaining_finding)
            if accepted_findings:
                ast = parse(linter.apply_fixes(ast, accepted_findings))
            return ast, len(accepted_findings), last_choice
        elif last_choice == "s":
            # Apply accepted findings and stop processing
            if accepted_findings:
                ast = parse(linter.apply_fixes(ast, accepted_findings))
            return ast, len(accepted_findings), last_choice
        elif last_choice == "q":
            print("Quitting without saving.")
            sys.exit(0)

    if accepted_findings:
        ast = parse(linter.apply_fixes(ast, accepted_findings))
        return ast, len(accepted_findings), last_choice

    return ast, 0, last_choice


def main():
    """Main entry point for the CLI tool."""
    parser = argparse.ArgumentParser(
        description="Lint and upgrade bash scripts from AWS CLI v1 to v2"
    )
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
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
        *create_all_hidden_alias_rules(),
        # Rules that do not automatically generate fixes go last
        EcrGetLoginRule(),
        CLIInputJSONRule(),
    ]

    if args.interactive:
        interactive_mode(rules, script_content, Path(args.output) if args.output else script_path)
    elif args.fix or args.output:
        auto_fix_mode(rules, script_content, Path(args.output) if args.output else script_path)
    else:
        dry_run_mode(rules, script_content, script_path)


if __name__ == "__main__":
    main()
