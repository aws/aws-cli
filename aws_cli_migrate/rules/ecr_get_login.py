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


class EcrGetLoginRule(LintRule):
    """Detects AWS CLI ECR get-login commands."""

    @property
    def name(self) -> str:
        return "ecr-get-login"

    @property
    def description(self) -> str:
        return (
            "In AWS CLI v2, The `aws ecr get-login` command has been removed. You must use "
            "`aws ecr get-login-password` instead. See "
            "https://docs.aws.amazon.com/cli/latest/userguide/"
            "cliv2-migration-changes.html#cliv2-migration-ecr-get-login."
        )

    def check(self, root: SgRoot) -> List[LintFinding]:
        """Check for AWS CLI ECR get-login commands."""
        node = root.root()
        nodes = node.find_all(
            all=[  # type: ignore[arg-type]
                {"kind": "command"},
                has_aws_command_any_kind(),
                {
                    "has": {
                        "kind": "word",
                        "pattern": "ecr",
                    }
                },
                {
                    "has": {
                        "kind": "word",
                        "pattern": "get-login",
                    }
                },
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
                    rule_name=self.name,
                    description=self.description,
                )
            )

        return findings
