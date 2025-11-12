from typing import List

from ast_grep_py.ast_grep_py import SgRoot

from awsclilinter.rules import LintFinding, LintRule


class PaginationRule(LintRule):
    """Detects AWS CLI commands missing --no-cli-paginate flag."""

    @property
    def name(self) -> str:
        return "no-cli-paginate"

    @property
    def description(self) -> str:
        return (
            "AWS CLI v2 uses pagination by default for commands that return large result sets. "
            "Add --no-cli-paginate to disable pagination and match v1 behavior."
        )

    def check(self, root: SgRoot, start_pos: int = 0) -> List[LintFinding]:
        """Check for AWS CLI commands missing --no-cli-paginate."""
        node = root.root()
        nodes = node.find_all(
            all=[
                {"kind": "command"},
                {"pattern": "aws $SERVICE $OPERATION $$$ARGS"},
                {"not": {"has": {"kind": "word", "pattern": "--no-cli-paginate"}}},
            ]
        )

        findings = []
        for stmt in nodes:
            if stmt.range().start.index < start_pos:
                continue
            original = stmt.text()
            suggested = original + " --no-cli-paginate"
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
