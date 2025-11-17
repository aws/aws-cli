from typing import List, Tuple

from ast_grep_py import SgRoot

from awsclilinter.rules import LintFinding, LintRule


class ScriptLinter:
    """Linter for bash scripts to detect AWS CLI v1 to v2 migration issues."""

    def __init__(self, rules: List[LintRule]):
        self.rules = rules

    def lint(self, script_content: str) -> List[Tuple[LintFinding, LintRule]]:
        """Lint the script and return all findings with their associated rules."""
        root = SgRoot(script_content, "bash")
        findings_with_rules = []
        for rule in self.rules:
            findings = rule.check(root)
            for finding in findings:
                findings_with_rules.append((finding, rule))
        return sorted(
            findings_with_rules, key=lambda fr: (fr[0].edit.start_pos, fr[0].edit.end_pos)
        )

    def lint_for_rule(self, script_content: str, rule: LintRule) -> List[LintFinding]:
        """Lint the script for a single rule.

        Args:
            script_content: The script content to lint
            rule: The rule to check

        Returns:
            List of findings for this rule, sorted by position
        """
        root = SgRoot(script_content, "bash")
        findings = rule.check(root)
        return sorted(findings, key=lambda f: (f.edit.start_pos, f.edit.end_pos))

    def apply_fixes(self, script_content: str, findings: List[LintFinding]) -> str:
        """Apply multiple fixes for a single rule.

        Args:
            script_content: The script content to modify
            findings: List of findings from a single rule to apply

        Returns:
            Modified script content
        """
        if not findings:
            return script_content

        root = SgRoot(script_content, "bash")
        node = root.root()

        # Collect all edits - they should be non-overlapping within a single rule
        edits = [f.edit for f in findings]

        return node.commit_edits(edits)
