# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from typing import List

from ast_grep_py.ast_grep_py import SgRoot

from aws_cli_migrate.rules import LintFinding, LintRule
from aws_cli_migrate.rules.utils import has_aws_command_any_kind


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
            "the input to be base64-encoded. If using a BLOB-type input parameter, retain v1 "
            "behavior after upgrading to AWS CLI v2 by adding "
            "`--cli-binary-format raw-in-base64-out`. See https://docs.aws.amazon.com/cli/"
            "latest/userguide/cliv2-migration-changes.html#cliv2-migration-binaryparam."
        )

    def check(self, root: SgRoot) -> List[LintFinding]:
        """Check for AWS CLI commands missing --cli-binary-format."""
        node = root.root()
        base64_broken_nodes = node.find_all(
            all=[  # type: ignore[arg-type]
                {"kind": "command"},
                has_aws_command_any_kind(),
                # Does not have the --cli-binary-format parameter
                # (unquoted, double-quoted, or single-quoted).
                {
                    "not": {
                        "has": {
                            "any": [
                                {
                                    "kind": "word",
                                    "pattern": "--cli-binary-format",
                                },
                                {"kind": "string", "pattern": '"--cli-binary-format"'},
                                {
                                    "kind": "raw_string",
                                    "pattern": "'--cli-binary-format'",
                                },
                            ]
                        }
                    }
                },
                # Command is not ecr-get-login, since it was removed in AWS CLI v2, and we don't
                # want to add v2-specific arguments to commands that don't exist in AWS CLI v2.
                {
                    "not": {
                        "all": [
                            {"has": {"kind": "word", "pattern": "ecr"}},
                            {"has": {"kind": "word", "pattern": "get-login"}},
                        ]
                    }
                },
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
