from typing import List

from ast_grep_py.ast_grep_py import SgRoot

from awsclilinter.rules import LintFinding, LintRule


class EcrGetLoginRule(LintRule):
    """Detects AWS CLI ECR get-login commands."""

    _SUGGESTED_MANUAL_FIX = (
        "Use `aws ecr get-login-password` instead, and pipe the results into the "
        "`docker login` command with the `--password-stdin` option. See "
        "https://docs.aws.amazon.com/cli/latest/userguide/"
        "cliv2-migration-changes.html#cliv2-migration-ecr-get-login.\n"
    )

    @property
    def name(self) -> str:
        return "ecr-get-login"

    @property
    def description(self) -> str:
        return (
            "In AWS CLI v2, The `ecr get-login` command has been removed. You must use "
            "`ecr get-login-password` instead. See https://docs.aws.amazon.com/cli/latest/userguide/"
            "cliv2-migration-changes.html#cliv2-migration-ecr-get-login.\n"
        )

    def check(self, root: SgRoot) -> List[LintFinding]:
        """Check for AWS CLI ECR get-login commands."""
        node = root.root()
        nodes = node.find_all(
            all=[  # type: ignore[arg-type]
                {"kind": "command"},
                {"has": {
                    "kind": "command_name",
                    "has": {
                        "kind": "word",
                        "pattern": "aws",
                    },
                }},
                {"has": {
                    "kind": "word",
                    "pattern": "ecr",
                }},
                {"has": {
                    "kind": "word",
                    "pattern": "get-login",
                }},
            ]
        )

        findings = []
        for stmt in nodes:
            findings.append(
                LintFinding(
                    line_start=stmt.range().start.line,
                    line_end=stmt.range().end.line,
                    edit=None,
                    original_text=stmt.text(),
                    suggested_manual_fix=self._SUGGESTED_MANUAL_FIX,
                    rule_name=self.name,
                    description=self.description,
                )
            )

        return findings
