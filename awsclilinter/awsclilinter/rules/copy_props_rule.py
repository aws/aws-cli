from typing import List

from ast_grep_py.ast_grep_py import SgRoot

from awsclilinter.rules import LintFinding, LintRule


class CopyPropsRule(LintRule):
    """Dummy test rule that adds --copy-props none to every AWS CLI command."""

    @property
    def name(self) -> str:
        return "copy-props-none"

    @property
    def description(self) -> str:
        return "Add --copy-props none to AWS CLI commands for testing multiple rules."

    def check(self, root: SgRoot, start_pos: int = 0) -> List[LintFinding]:
        """Check for AWS CLI commands missing --copy-props none."""
        node = root.root()
        nodes = node.find_all(
            all=[
                {"kind": "command"},
                {"pattern": "aws $SERVICE $OPERATION $$$ARGS"},
                {"not": {"has": {"kind": "word", "pattern": "--copy-props"}}},
            ]
        )

        findings = []
        for stmt in nodes:
            # Skip nodes before start_pos
            if stmt.range().start.index < start_pos:
                continue

            original = stmt.text()
            suggested = original + " --copy-props none"
            edit = stmt.replace(suggested)

            findings.append(
                LintFinding(
                    line_start=stmt.range().start.line,
                    line_end=stmt.range().end.line,
                    edit=edit,
                    original_text=original,
                    rule_name=self.name,
                    description=self.description,
                )
            )

        return findings
