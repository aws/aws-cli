from typing import List

from ast_grep_py.ast_grep_py import SgRoot

from awsclilinter.rules import LintFinding, LintRule


class Base64BinaryFormatRule(LintRule):
    """Detects any AWS CLI command that does not specify the --cli-binary-format. This mitigates
    the breaking change with how AWS CLI v2 treats binary parameters."""

    @property
    def name(self) -> str:
        return "binary-params-base64"

    @property
    def description(self) -> str:
        return (
            "In AWS CLI v2, an input parameter typed as binary large object (BLOB) expects "
            "the input to be base64-encoded. To retain v1 behavior after upgrading to AWS CLI v2, "
            "add `--cli-binary-format raw-in-base64-out`."
        )

    def check(self, root: SgRoot) -> List[LintFinding]:
        """Check for AWS CLI commands missing --cli-binary-format."""
        node = root.root()
        base64_broken_nodes = node.find_all(
            all=[  # type: ignore[arg-type]
                {"kind": "command"},
                {"pattern": "aws $SERVICE $OPERATION $$$ARGS"},
                {"not": {"has": {"kind": "word", "pattern": "--cli-binary-format"}}},
            ]
        )

        findings = []
        for stmt in base64_broken_nodes:
            original = stmt.text()
            # To retain v1 behavior after migrating to v2, append
            # --cli-binary-format raw-in-base64-out
            suggested = original + " --cli-binary-format raw-in-base64-out"
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
