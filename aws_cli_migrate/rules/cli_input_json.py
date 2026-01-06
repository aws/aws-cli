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


class CLIInputJSONRule(LintRule):
    """Detects AWS CLI commands that use the `--cli-input-json` parameter."""

    _SUGGESTED_MANUAL_FIX = (
        "If pagination-related parameters are present in the input JSON specified with "
        "`--cli-input-json`, remove the pagination parameters from the input JSON "
        "to retain v1 behavior. Alternatively, migrate to v2 behavior by moving the pagination "
        "parameters from the input JSON onto the command as separate command line parameters. "
        "See https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html"
        "#cliv2-migration-skeleton-paging.\n"
    )

    @property
    def name(self) -> str:
        return "cli-input-json"

    @property
    def auto_fixable(self) -> bool:
        """Return whether the rule's check() function returns auto_fixable LintFindings."""
        return True

    @property
    def description(self) -> str:
        return (
            "In AWS CLI v2, specifying pagination parameters via `--cli-input-json` "
            "will turn off automatic pagination. See https://docs.aws.amazon.com/cli/"
            "latest/userguide/cliv2-migration-changes.html#cliv2-migration-skeleton-paging.\n"
        )

    def check(self, root: SgRoot) -> List[LintFinding]:
        """Check for AWS CLI commands that use `--cli-input-json`."""
        node = root.root()
        nodes = node.find_all(
            all=[  # type: ignore[arg-type]
                {"kind": "command"},
                has_aws_command_any_kind(),
                # Has the --cli-input-json parameter (unquoted, double-quoted, or single-quoted).
                {
                    "has": {
                        "any": [
                            {
                                "kind": "word",
                                "pattern": "--cli-input-json",
                            },
                            {
                                "kind": "string",
                                "pattern": '"--cli-input-json"',
                            },
                            {
                                "kind": "raw_string",
                                "pattern": "'--cli-input-json'",
                            },
                        ]
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
                    suggested_manual_fix=self._SUGGESTED_MANUAL_FIX,
                    rule_name=self.name,
                    description=self.description,
                )
            )

        return findings
