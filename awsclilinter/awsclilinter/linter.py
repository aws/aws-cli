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
    ) -> Tuple[LintFinding, SgRoot]:
        """Re-lint from cursor position and return the first finding and parsed root.

        Returns:
            Tuple of (finding, root). The root can be reused in apply_single_fix to
            avoid re-parsing.

        Raises:
            RuntimeError: If no finding is found after cursor_pos. This should never
            happen as our rules are designed such that fixing one finding never
            inadvertently resolves another.
        """
        root = SgRoot(script_content, "bash")
        findings = rule.check(root, start_pos=cursor_pos)
        if not findings:
            raise RuntimeError(
                f"Expected to find at least one issue for rule '{rule.name}' after position "
                f"{cursor_pos}, but found none. This indicates a rule fix inadvertently "
                f"resolved another finding, which should not happen."
            )
        return (findings[0], root)
