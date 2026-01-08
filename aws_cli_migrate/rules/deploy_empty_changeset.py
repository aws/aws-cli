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


class DeployEmptyChangesetRule(LintRule):
    """Detects AWS CLI CloudFormation deploy commands."""

    @property
    def name(self) -> str:
        return "deploy-empty-changeset"

    @property
    def description(self) -> str:
        return (
            "In AWS CLI v2, deploying an AWS CloudFormation Template that results in an empty "
            "changeset will NOT result in an error. You can add the --fail-on-empty-changeset "
            "flag to retain v1 behavior in v2. See https://docs.aws.amazon.com/cli/latest/"
            "userguide/cliv2-migration-changes.html#cliv2-migration-cfn."
        )

    def check(self, root: SgRoot) -> List[LintFinding]:
        """Check for AWS CLI CloudFormation deploy commands
        without the --fail-on-empty-changeset or --no-fail-on-empty-changeset arguments.
        """
        node = root.root()
        nodes = node.find_all(
            all=[  # type: ignore[arg-type]
                {"kind": "command"},
                has_aws_command_any_kind(),
                {
                    "has": {
                        "kind": "word",
                        "pattern": "cloudformation",
                    }
                },
                {
                    "has": {
                        "kind": "word",
                        "pattern": "deploy",
                    }
                },
                {"not": {"has": {"kind": "word", "pattern": "--fail-on-empty-changeset"}}},
                {"not": {"has": {"kind": "word", "pattern": "--no-fail-on-empty-changeset"}}},
            ]
        )

        findings = []
        for stmt in nodes:
            original = stmt.text()
            suggested = original + " --fail-on-empty-changeset"
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
