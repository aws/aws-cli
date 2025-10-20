from typing import List

from awsclilinter.rules_base import LintFinding, LintRule


class Base64BinaryFormatRule(LintRule):
    """Detects AWS CLI commands with file:// that need --cli-binary-format."""

    @property
    def name(self) -> str:
        return "base64-binary-format"

    @property
    def description(self) -> str:
        return (
            "AWS CLI v2 requires --cli-binary-format raw-in-base64-out "
            "for commands using file:// protocol"
        )

    def check(self, root) -> List[LintFinding]:
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
            service = stmt.get_match("SERVICE").text()
            operation = stmt.get_match("OPERATION").text()
            args = " ".join([match.text() for match in stmt.get_multiple_matches("ARGS")])

            original = stmt.text()
            suggested = f"aws {service} {operation} {args} --cli-binary-format raw-in-base64-out"

            findings.append(
                LintFinding(
                    line_start=stmt.range().start.line,
                    line_end=stmt.range().end.line,
                    original_text=original,
                    suggested_fix=suggested,
                    rule_name=self.name,
                    description=self.description,
                )
            )

        return findings
