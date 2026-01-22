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
import re
import sys
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional, Tuple

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


class UserChoice(Enum):
    YES = auto()
    NO = auto()
    ACCEPT_ALL_OF_TYPE = auto()
    REJECT_ALL_OF_TYPE = auto()
    UPDATE_ALL = auto()
    SAVE_EXIT = auto()
    QUIT = auto()
    NEXT = auto()


def _color_text(text, color_code):
    """Colorize text for terminal output only if a TTY is available."""
    if sys.stdout.isatty():
        return f"{color_code}{text}{RESET}"
    return text


def _prompt_user_choice_interactive_mode(auto_fixable: bool = True) -> UserChoice:
    """Get user input for interactive mode."""
    _AUTO_FIX_CHOICE_MAP = {
        "y": UserChoice.YES,
        "n": UserChoice.NO,
        "a": UserChoice.ACCEPT_ALL_OF_TYPE,
        "r": UserChoice.REJECT_ALL_OF_TYPE,
        "u": UserChoice.UPDATE_ALL,
        "s": UserChoice.SAVE_EXIT,
        "q": UserChoice.QUIT,
    }
    _NON_AUTO_FIX_CHOICE_MAP = {
        "n": UserChoice.NEXT,
        "s": UserChoice.SAVE_EXIT,
        "q": UserChoice.QUIT,
    }
    while True:
        if auto_fixable:
            choice = (
                input(
                    "\nApply this fix? [y] yes, [n] no, [a] accept all of type, "
                    "[r] reject all of type, [u] update all, [s] save and exit, [q] quit: "
                )
                .lower()
                .strip()
            )
            if choice in _AUTO_FIX_CHOICE_MAP:
                return _AUTO_FIX_CHOICE_MAP[choice]
            print("Invalid choice. Please enter y, n, a, r, u, s, or q.")
        else:
            choice = input("\n[n] next, [s] save, [q] quit: ").lower().strip()
            if choice in _NON_AUTO_FIX_CHOICE_MAP:
                return _NON_AUTO_FIX_CHOICE_MAP[choice]
            print("Invalid choice. Please enter n, s, or q.")


def _summarize_non_fixable_findings(
    non_auto_fixable_findings: List[LintFinding], script_content: str, input_path: Path
):
    """Summarize the input non-fixable findings."""
    warning_header = _color_text(
        f"️{len(non_auto_fixable_findings)} issue(s) require manual review:", YELLOW
    )
    print(f"\n{warning_header}\n")
    for finding in non_auto_fixable_findings:
        _display_finding(finding, script_content, input_path)


def _display_finding(finding: LintFinding, script_content: str, input_path: Path):
    """Display a finding to the user with context. This function relies on the assumption that
    auto-fixes will never change the number of lines in the script.
    """
    if finding.auto_fixable:
        context_starting_line = None
        line_num_width = None
        src_issue_line = None
        # Apply the edit to get the fixed content
        fixed_content = (
            script_content[: finding.edit.start_pos]
            + finding.edit.inserted_text
            + script_content[finding.edit.end_pos :]
        )

        diff = difflib.unified_diff(
            script_content.splitlines(), fixed_content.splitlines(), n=CONTEXT_SIZE, lineterm=""
        )
        for line_num, line in enumerate(diff):
            if line_num < 2:
                # First 2 lines are the --- and +++ lines, we don't print those.
                continue
            elif line_num == 2:
                # The 3rd line is the context control line.
                match = re.search(r"@@ -(\d+)(?:,(\d+))?\s+\+", line)

                if not match:
                    # group(1) is always the starting line number 'x'
                    raise RuntimeError(f"Expected context control line. Received: {line}")
                context_starting_line = int(match.group(1))
                # If the context size is not specified in the control line, the context is
                # exactly 1 line long.
                context_size = int(match.group(2)) if match.group(2) else 1
                context_end_line = context_starting_line + context_size
                line_num_width = len(str(context_end_line))
                continue
            elif line.startswith("-"):
                # Removed line
                src_issue_line = int(
                    str(context_starting_line + line_num - 3).rjust(line_num_width)
                )
                line_prefix = (
                    f"{str(src_issue_line).rjust(line_num_width)} " + " " * line_num_width + "│"
                )
                print(f"{line_prefix}{_color_text(line, RED)}")
            elif line.startswith("+"):
                # Added line
                dest_issue_line = int(
                    str(context_starting_line + line_num - 4).rjust(line_num_width)
                )
                line_prefix = (
                    " " * line_num_width + f" {str(dest_issue_line).rjust(line_num_width)}" + "│"
                )
                print(f"{line_prefix}{_color_text(line, GREEN)}")
            else:
                # Context (unchanged) lines always start with whitespace.
                # If we already rendered the deleted/added lines, we must offset the line number
                # to account for not printing a source/dest line for the deleted/added lines.
                offset = 3 if src_issue_line is None else 4
                raw_line_num = str(context_starting_line + line_num - offset).rjust(line_num_width)
                line_prefix = f"{raw_line_num} {raw_line_num}│"
                print(f"{line_prefix}{line}")
        print(f"\n{input_path}:{src_issue_line} [{finding.rule_name}] {finding.description}")
    else:
        # Non-fixable issue - show only the problematic lines
        src_lines = script_content.splitlines()
        start_line = finding.line_start
        end_line = finding.line_end
        context_start_line = max(0, start_line - CONTEXT_SIZE)
        context_end_line = min(len(src_lines), end_line + CONTEXT_SIZE + 1)
        line_num_width = len(str(context_end_line))

        for i in range(context_start_line, context_end_line):
            line = src_lines[i]
            if start_line <= i <= end_line:
                raw_line_num = str(i + 1).rjust(line_num_width)
                line_prefix = f"{raw_line_num} {raw_line_num}│"
                print(f"{line_prefix}{_color_text(line, YELLOW)}")
            else:
                raw_line_num = str(i + 1).rjust(line_num_width)
                line_prefix = f"{raw_line_num} {raw_line_num}│"
                print(f"{line_prefix}{line}")

        manual_review_required_text = _color_text("[MANUAL REVIEW REQUIRED]", YELLOW)
        print(
            f"\n{input_path}:{start_line + 1} {manual_review_required_text} "
            f"[{finding.rule_name}] {finding.description}"
        )


def _interactive_prompt_for_rule(
    findings: List[LintFinding],
    script_content: str,
    input_path: Path,
) -> Tuple[List[LintFinding], Optional[UserChoice]]:
    """Execute interactive prompting for a single rule's findings. For each finding,
    the user will be prompted to enter a control code; the control code options
    depends on whether the finding is auto-fixable.

    This function returns a list of the accepted findings, and the last choice selected by the
    user.

    Args:
        findings: List of findings for this rule.
        script_content: Current script content.
        input_path: The path to the input script.

    Returns:
        Tuple of (accepted_findings, last_choice)
        accepted_findings the findings accepted by the user.
        last_choice is the last choice entered by the user.
    """
    accepted_findings: List[LintFinding] = []
    last_choice: Optional[UserChoice] = None

    for i, finding in enumerate(findings):
        print()
        _display_finding(finding, script_content, input_path)
        last_choice = _prompt_user_choice_interactive_mode(auto_fixable=finding.auto_fixable)

        if not finding.auto_fixable:
            # Non-fixable finding - only allow next, save, or quit
            if last_choice == UserChoice.QUIT or last_choice == UserChoice.SAVE_EXIT:
                # User's choice was 'quit'/'save', which is terminal.
                return accepted_findings, last_choice
            elif last_choice == UserChoice.NEXT:
                # User's choice was 'next'.
                continue
            else:
                raise RuntimeError(f"Unexpected value of last_choice: {last_choice}")
        else:
            if last_choice == UserChoice.YES:
                accepted_findings.append(finding)
            elif last_choice == UserChoice.NO:
                # User rejected the suggested fix from the finding.
                continue
            elif last_choice == UserChoice.ACCEPT_ALL_OF_TYPE:
                # User's choice was 'accept all of type'. Accept all remaining findings
                # of this rule type including the current one.
                accepted_findings.extend(f for f in findings[i:] if f.auto_fixable)
                return accepted_findings, last_choice
            elif last_choice == UserChoice.REJECT_ALL_OF_TYPE:
                # User's choice was 'reject all of type'. Reject all remaining findings
                # of this rule type.
                return accepted_findings, last_choice
            elif last_choice == UserChoice.UPDATE_ALL:
                # User's choice was 'update all'. Accept all remaining findings
                # including the current one.
                accepted_findings.extend(f for f in findings[i:] if f.auto_fixable)
                return accepted_findings, last_choice
            elif last_choice == UserChoice.SAVE_EXIT or last_choice == UserChoice.QUIT:
                # User's choice was 'save'/'quit', which is terminal.
                return accepted_findings, last_choice
            else:
                raise RuntimeError(f"Unexpected value of last_choice: {last_choice}")

    return accepted_findings, last_choice


def auto_fix_mode(
    rules: List[LintRule],
    script_content: str,
    input_path: Path,
    output_path: Path,
):
    """Handler for auto-fix mode. Lints the input script based on the input rules list. If
    any findings were detected that can be automatically fixed, applies the automatic
    fixes to the script and writes it to the output path.

    Args:
        rules: List of linting rules to run against the input script.
        script_content: Current script represented as an AST.
        input_path: The path to the input script.
        output_path: The path to write the updated script if any findings were detected.
    """
    current_ast = parse(script_content)
    # Sequence of updates made to the script. Index i is the state of the script before
    # applying the fixes for the i'th rule, if any.
    script_states: List[str] = []
    findings_with_script_index: List[Tuple[LintFinding, int]] = []
    num_auto_fixes_applied = 0
    num_manual_review_issues = 0

    for rule in rules:
        rule_findings = linter.lint_for_rule(current_ast, rule)

        if not rule_findings:
            continue

        # Store the finding, and an index that points to the current state of the script.
        script_states.append(current_ast.root().text())
        findings_with_script_index.extend(
            [(finding, len(script_states) - 1) for finding in rule_findings]
        )

        auto_fixable_findings = [f for f in rule_findings if f.auto_fixable]
        num_auto_fixes_applied += len(auto_fixable_findings)
        num_manual_review_issues += len([f for f in rule_findings if not f.auto_fixable])

        current_ast = (
            parse(linter.apply_fixes(current_ast, auto_fixable_findings))
            if auto_fixable_findings
            else current_ast
        )

    if not findings_with_script_index:
        print(f"\n{input_path}: No issues found.")
        return

    for i, (finding, ast_index) in enumerate(findings_with_script_index):
        if i == 0:
            print()
        else:
            print("\n---\n")
        _display_finding(finding, script_states[ast_index], input_path)

    print()
    print(
        f"Found {len(findings_with_script_index)} issue(s). "
        f"{num_auto_fixes_applied} fixed. "
        f"{num_manual_review_issues} require(s) manual review."
    )

    # Write the updated script if any auto-fixes were applied.
    if num_auto_fixes_applied:
        output_path.write_text(current_ast.root().text())
        print(f"Changes written to: {output_path}")
    else:
        print("No changes to write.")


def dry_run_mode(
    rules: List[LintRule],
    script_content: str,
    input_path: Path,
):
    """Handler for dry-run mode. Lints the input script based on the input rules list and
    summarizes the findings without writing any changes to disk.

    Args:
        rules: List of linting rules to run against the input script.
        script_content: The input script.
        input_path: The path to the input script.
    """
    current_ast = parse(script_content)
    # Sequence of updates made to the script. Index i is the state of the script before
    # applying the fixes for the i'th rule, if any.
    script_states: List[str] = []
    findings_with_script_index: List[Tuple[LintFinding, int]] = []
    num_auto_fixable_findings = 0
    num_manual_review_findings = 0

    for rule in rules:
        rule_findings = linter.lint_for_rule(current_ast, rule)

        if not rule_findings:
            continue

        # Store the finding, and an index that points to the current state of the script.
        script_states.append(current_ast.root().text())
        findings_with_script_index.extend(
            [(finding, len(script_states) - 1) for finding in rule_findings]
        )

        auto_fixable_findings = [f for f in rule_findings if f.auto_fixable]
        num_auto_fixable_findings += len(auto_fixable_findings)
        num_manual_review_findings += len([f for f in rule_findings if not f.auto_fixable])

        current_ast = (
            parse(linter.apply_fixes(current_ast, auto_fixable_findings))
            if auto_fixable_findings
            else current_ast
        )

    if not findings_with_script_index:
        print(f"\n{input_path}: No issues found.")
        return

    for i, (finding, ast_index) in enumerate(findings_with_script_index):
        if i == 0:
            print()
        else:
            print("\n---\n")
        _display_finding(finding, script_states[ast_index], input_path)

    print()
    print(
        f"Found {len(findings_with_script_index)} issue(s). "
        f"{num_auto_fixable_findings} fixable with the `--fix` option. "
        f"{num_manual_review_findings} require(s) manual review."
    )


def interactive_mode(
    rules: List[LintRule],
    script_content: str,
    input_path: Path,
    output_path: Path,
):
    """Handler for interactive mode. Lints the input script based on the input rules list and
    interactively prompts the user to address each fix.

    Args:
        rules: List of linting rules to run against the input script.
        script_content: The input script.
        input_path: Path to the input script.
        output_path: The path to write the script to, if updated.
    """
    current_ast = parse(script_content)
    auto_apply = False
    findings_found = 0
    num_auto_fixes_available = 0
    num_auto_fixes_applied = 0
    num_manual_review_issues = 0
    non_auto_fixable_findings_to_summarize: List[LintFinding] = []

    for rule in rules:
        rule_findings = linter.lint_for_rule(current_ast, rule)
        num_auto_fixes_available += len([f for f in rule_findings if f.auto_fixable])
        num_manual_review_issues += len([f for f in rule_findings if not f.auto_fixable])

        if not rule_findings:
            continue

        if auto_apply:
            # Since we are in auto-apply mode, we do not prompt the user and instead
            # automatically accept all findings for this rule.
            accepted_findings = rule_findings
            last_choice: Optional[UserChoice] = None
        else:
            accepted_findings, last_choice = _interactive_prompt_for_rule(
                rule_findings, current_ast.root().text(), input_path
            )
        auto_fixable_findings = [f for f in accepted_findings if f.auto_fixable]
        num_auto_fixes_applied += len(auto_fixable_findings)
        findings_found += len(rule_findings)
        if last_choice == UserChoice.QUIT:
            # User selected 'quit'.
            print("Quit without saving.")
            return
        elif last_choice == UserChoice.SAVE_EXIT:
            # Update the AST if any of the accepted findings were auto-fixable.
            current_ast = (
                parse(linter.apply_fixes(current_ast, auto_fixable_findings))
                if auto_fixable_findings
                else current_ast
            )
            # Write the updated script if any auto-fixes were applied.
            break
        elif last_choice == UserChoice.UPDATE_ALL:
            # Update the AST if any of the accepted findings were auto-fixable.
            current_ast = (
                parse(linter.apply_fixes(current_ast, auto_fixable_findings))
                if auto_fixable_findings
                else current_ast
            )
            # Store the findings that were not auto-fixable for final summarization.
            non_auto_fixable_findings_to_summarize.extend(
                f for f in rule_findings if not f.auto_fixable
            )
            # Enable auto_apply so subsequent rules will automatically
            # accept and apply findings.
            auto_apply = True
        elif (
            last_choice == UserChoice.YES
            or last_choice == UserChoice.NO
            or last_choice == UserChoice.ACCEPT_ALL_OF_TYPE
            or last_choice == UserChoice.REJECT_ALL_OF_TYPE
        ):
            # Update the AST if any of the accepted findings were auto-fixable.
            current_ast = (
                parse(linter.apply_fixes(current_ast, auto_fixable_findings))
                if auto_fixable_findings
                else current_ast
            )
        elif last_choice == UserChoice.NEXT:
            # If last_choice is Next, then we know the last finding displayed for this rule
            # was not auto-fixable. We'll still update the AST with any auto-fixable findings.
            # Note that if "The last finding for this rule is not auto-fixable implies no
            # findings for this rule are auto-fixable" is a true assumption, then applying
            # auto-fixes in this case is a no-op. As of version 1.0.0, this assumption is true,
            # but we'll leave open the possibility that it is not true in the future.
            # Update the AST if any of the accepted findings were auto-fixable.
            current_ast = (
                parse(linter.apply_fixes(current_ast, auto_fixable_findings))
                if auto_fixable_findings
                else current_ast
            )
        elif last_choice is None and auto_apply:
            # In auto-apply mode, we apply all auto-fixes and store any findings that were not
            # auto-fixable for final summarization.
            # Update the AST if any of the accepted findings were auto-fixable.
            current_ast = (
                parse(linter.apply_fixes(current_ast, auto_fixable_findings))
                if auto_fixable_findings
                else current_ast
            )
            # Store the findings that were not auto-fixable for final summarization.
            non_auto_fixable_findings_to_summarize.extend(
                f for f in rule_findings if not f.auto_fixable
            )
        else:
            raise RuntimeError(
                f"Unexpected value of (last_choice, auto_apply): {(last_choice, auto_apply)}"
            )

    print()

    if findings_found == 0:
        print(f"{input_path}: No issues found.")
        return

    # Summarize the non-auto-fixable findings, if any.
    if non_auto_fixable_findings_to_summarize:
        _summarize_non_fixable_findings(
            non_auto_fixable_findings_to_summarize, current_ast.root().text(), input_path
        )

    print(
        f"Found {findings_found} issue(s). "
        f"{num_auto_fixes_applied} fixed. "
        f"{num_manual_review_issues} require(s) manual review."
    )

    # Write the updated script if any auto-fixes were applied.
    if num_auto_fixes_applied:
        output_path.write_text(current_ast.root().text())
        print(f"Changes written to: {output_path}")
    else:
        print("No changes to write.")


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
        interactive_mode(
            rules, script_content, script_path, Path(args.output) if args.output else script_path
        )
    elif args.fix:
        auto_fix_mode(
            rules, script_content, script_path, Path(args.output) if args.output else script_path
        )
    else:
        dry_run_mode(rules, script_content, script_path)


if __name__ == "__main__":
    main()
