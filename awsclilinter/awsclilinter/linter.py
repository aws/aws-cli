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

    def apply_single_fix(
        self, script_content: str, finding: LintFinding, root: SgRoot | None = None
    ) -> str:
        """Apply a single fix to the script content.

        Args:
            script_content: The script content to modify
            finding: The finding with edit to apply
            root: Optional pre-parsed SgRoot to reuse (avoids re-parsing)
        """
        if root is None:
            root = SgRoot(script_content, "bash")
        node = root.root()
        return node.commit_edits([finding.edit])

    def refresh_finding(
        self, script_content: str, rule: LintRule, cursor_pos: int
    ) -> Tuple[LintFinding, SgRoot] | None:
        """Re-lint from cursor position and return the first finding and parsed root.

        Returns:
            Tuple of (finding, root) if found, None otherwise. The root can be reused
            in apply_single_fix to avoid re-parsing.
        """
        root = SgRoot(script_content, "bash")
        findings = rule.check(root, start_pos=cursor_pos)
        return (findings[0], root) if findings else None
