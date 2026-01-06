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
from typing import List, Tuple

from ast_grep_py.ast_grep_py import SgRoot

from aws_cli_migrate.rules import LintFinding, LintRule


def parse(script_content: str) -> SgRoot:
    """Parse the bash script content into an AST."""
    return SgRoot(script_content, "bash")


def lint(ast: SgRoot, rules: List[LintRule]) -> List[Tuple[LintFinding, LintRule]]:
    """Lint the AST and return all findings with their associated rules."""
    findings_with_rules = []
    for rule in rules:
        findings = rule.check(ast)
        for finding in findings:
            findings_with_rules.append((finding, rule))
    return sorted(
        findings_with_rules,
        key=lambda fr: (
            fr[0].edit.start_pos if fr[0].edit else fr[0].line_start,
            fr[0].edit.end_pos if fr[0].edit else fr[0].line_end,
        ),
    )


def lint_for_rule(ast: SgRoot, rule: LintRule) -> List[LintFinding]:
    """Lint the script for a single rule.

    Args:
        ast: The AST to lint for the rule.
        rule: The rule to check.

    Returns:
        List of findings for this rule, sorted by position (ascending)
    """
    findings = rule.check(ast)
    return sorted(
        findings,
        key=lambda f: (
            f.edit.start_pos if f.edit else f.line_start,
            f.edit.end_pos if f.edit else f.line_end,
        ),
    )


def apply_fixes(ast: SgRoot, findings: List[LintFinding]) -> str:
    """Apply to the AST for a single rule.

    Args:
        ast: The AST representation of the script to apply fixes to.
        findings: List of findings from a single rule to apply.

    Returns:
        Modified script content
    """
    root = ast.root()
    if not findings:
        return root.text()

    # Collect all edits - they should be non-overlapping within a single rule
    # Filter out non-fixable findings
    edits = [f.edit for f in findings if f.auto_fixable]
    if not edits:
        return root.text()
    return root.commit_edits(edits)
