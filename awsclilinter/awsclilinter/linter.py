from typing import List

from ast_grep_py import SgRoot

from awsclilinter.rules_base import LintFinding, LintRule


class ScriptLinter:
    """Linter for bash scripts to detect AWS CLI v1 to v2 migration issues."""

    def __init__(self, rules: List[LintRule]):
        self.rules = rules

    def lint(self, script_content: str) -> List[LintFinding]:
        """Lint the script and return all findings."""
        root = SgRoot(script_content, "bash")
        findings = []
        for rule in self.rules:
            findings.extend(rule.check(root))
        return sorted(findings, key=lambda f: (f.line_start, f.line_end))

    def apply_fixes(self, script_content: str, findings: List[LintFinding]) -> str:
        """Apply fixes to the script content."""
        root = SgRoot(script_content, "bash")
        node = root.root()

        edits = []
        for finding in findings:
            matches = node.find_all(pattern=finding.original_text)
            for match in matches:
                edits.append(match.replace(finding.suggested_fix))

        return node.commit_edits(edits)
