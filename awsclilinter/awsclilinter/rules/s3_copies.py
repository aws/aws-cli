from typing import List

from ast_grep_py.ast_grep_py import SgRoot

from awsclilinter.rules import LintFinding, LintRule


class S3CopyRule(LintRule):
    """Detects AWS CLI high-level s3 cp/mv/sync bucket-to-bucket commands."""

    @property
    def name(self) -> str:
        return "s3-copy"

    @property
    def description(self) -> str:
        return (
            "In AWS CLI v2, object properties will be copied from the source in multipart "
            "copies between S3 buckets. If a copy is or becomes multipart after upgrading to "
            "AWS CLI v2, extra API calls will be made. See https://docs.aws.amazon.com/cli/latest/"
            "userguide/cliv2-migration-changes.html#cliv2-migration-s3-copy-metadata."
        )

    def check(self, root: SgRoot) -> List[LintFinding]:
        """Check for AWS CLI s3 cp/mv/sync bucket-to-bucket
        commands without --copy-props argument.
        """
        node = root.root()
        nodes = node.find_all(
            all=[  # type: ignore[arg-type]
                {"kind": "command"},
                {
                    "any": [
                        {"pattern": "aws s3 cp"},
                        {"pattern": "aws s3 mv"},
                        {"pattern": "aws s3 sync"},
                    ]
                },
                {"has": {"kind": "word", "regex": "\\As3://"}},
                {
                    "has": {
                        "kind": "word",
                        "regex": "\\As3://",
                        "follows": {"stopBy": "end", "kind": "word", "regex": "\\As3://"},
                    }
                },
                {"not": {"has": {"kind": "word", "pattern": "--copy-props"}}},
            ]
        )

        findings = []
        for stmt in nodes:
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
