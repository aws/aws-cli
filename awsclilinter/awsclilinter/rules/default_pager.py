from typing import List

from ast_grep_py.ast_grep_py import SgRoot

from awsclilinter.rules import LintFinding, LintRule


class DefaultPagerRule(LintRule):
    """Detects AWS CLI commands missing --no-cli-pager flag."""

    @property
    def name(self) -> str:
        return "pager-by-default"

    @property
    def description(self) -> str:
        return (
            "AWS CLI v2 uses the system pager by default for all command output. "
            "Add --no-cli-pager to disable use of the pager and match v1 behavior. See "
            "https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html"
            "#cliv2-migration-output-pager."
        )

    def check(self, root: SgRoot) -> List[LintFinding]:
        """Check for AWS CLI commands missing --no-cli-pager."""
        node = root.root()
        nodes = node.find_all(
            all=[  # type: ignore[arg-type]
                {"kind": "command"},
                {"pattern": "aws $SERVICE $OPERATION $$$ARGS"},
                {"not": {"has": {"kind": "word", "pattern": "--no-cli-pager"}}},
            ]
        )

        findings = []
        for stmt in nodes:
            original = stmt.text()
            suggested = original + " --no-cli-pager"
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
