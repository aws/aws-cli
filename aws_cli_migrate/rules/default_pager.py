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


class DefaultPagerRule(LintRule):
    """Detects AWS CLI commands missing --no-cli-pager flag."""

    @property
    def name(self) -> str:
        return "pager-by-default"

    @property
    def description(self) -> str:
        return (
            "AWS CLI v2 uses the system pager by default for all command output. "
            "Add `--no-cli-pager` to disable use of the pager and match v1 behavior. See "
            "https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html"
            "#cliv2-migration-output-pager."
        )

    def check(self, root: SgRoot) -> List[LintFinding]:
        """Check for AWS CLI commands missing --no-cli-pager."""
        node = root.root()
        nodes = node.find_all(
            all=[  # type: ignore[arg-type]
                {"kind": "command"},
                has_aws_command_any_kind(),
                # Does not have the --no-cli-pager parameter
                # (unquoted, double-quoted, or single-quoted).
                {
                    "not": {
                        "has": {
                            "any": [
                                {
                                    "kind": "word",
                                    "pattern": "--no-cli-pager",
                                },
                                {
                                    "kind": "string",
                                    "pattern": '"--no-cli-pager"',
                                },
                                {
                                    "kind": "raw_string",
                                    "pattern": "'--no-cli-pager'",
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
