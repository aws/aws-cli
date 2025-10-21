from typing import List

from ast_grep_py.ast_grep_py import SgRoot

from awsclilinter.rules_base import LintFinding, LintRule


class Base64BinaryFormatRule(LintRule):
    """Detects AWS CLI commands with file:// that need --cli-binary-format. This is a best-effort
    attempt at statically detecting the breaking change with how AWS CLI v2 treats binary
    parameters."""

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
        """Check for AWS CLI commands with file:// missing --cli-binary-format."""
        node = root.root()
        base64_broken_nodes = node.find_all(
            all=[
                {"kind": "command"},
                {"pattern": "aws $SERVICE $OPERATION $$$ARGS"},
                {"has": {"kind": "word", "regex": r"\Afile://"}},
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

            print(f"suggested fix: {suggested}")
            print(f"edit text: {edit.inserted_text}")

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
