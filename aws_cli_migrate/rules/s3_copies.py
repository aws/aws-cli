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


class S3CopyRule(LintRule):
    """Detects AWS CLI high-level s3 cp/mv/sync bucket-to-bucket commands."""

    def _follows_s3_bucket_any_kind(self):
        # Returns a rule that ensures the pattern comes after an S3 bucket.
        return {
            "follows": {
                "stopBy": "end",
                "any": [
                    # Occurs after unquoted S3 bucket (e.g. s3://bucket).
                    {
                        "kind": "word",
                        "regex": "\\As3://",
                    },
                    # Occurs after double-quoted S3 bucket (e.g. "s3://bucket").
                    {
                        "kind": "string",
                        "has": {
                            "kind": "string_content",
                            "nthChild": 1,
                            "regex": "\\As3://",
                        },
                    },
                    # Occurs after raw-string S3 bucket (e.g. 's3://bucket').
                    {
                        "kind": "raw_string",
                        "regex": "'s3://[^']+'",
                    },
                    # Occurs after concatenated S3 bucket (e.g. s3://$S3_BUCKET_NAME).
                    {
                        "kind": "concatenation",
                        "has": {
                            "any": [
                                {
                                    "kind": "word",
                                    "regex": "\\As3://",
                                },
                                {
                                    "kind": "string",
                                    "has": {
                                        "kind": "string_content",
                                        "nthChild": 1,
                                        "regex": "\\As3://",
                                    },
                                },
                                {
                                    "kind": "raw_string",
                                    "regex": "'s3://[^']+'",
                                },
                            ]
                        },
                    },
                ],
            }
        }

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
                has_aws_command_any_kind(),
                {
                    "has": {
                        "kind": "word",
                        "pattern": "s3",
                    }
                },
                # The command is either cp, mv, or sync
                {
                    "has": {
                        "any": [
                            {
                                "kind": "word",
                                "pattern": "cp",
                            },
                            {
                                "kind": "word",
                                "pattern": "mv",
                            },
                            {
                                "kind": "word",
                                "pattern": "sync",
                            },
                        ]
                    }
                },
                # The command has two S3 buckets (signifies a bucket-to-bucket copy).
                {
                    "has": {
                        "any": [
                            # Has an S3 bucket followed by an unquoted S3 bucket (e.g. s3://bucket).
                            {
                                "kind": "word",
                                "regex": "\\As3://",
                                **self._follows_s3_bucket_any_kind(),
                            },
                            # Has an S3 bucket followed by a
                            # double-quoted S3 bucket (e.g. "s3://bucket").
                            {
                                "kind": "string",
                                "has": {
                                    "kind": "string_content",
                                    "nthChild": 1,
                                    "regex": "\\As3://",
                                },
                                **self._follows_s3_bucket_any_kind(),
                            },
                            # Has an S3 bucket followed by a
                            # raw-string S3 bucket (e.g. 's3://bucket').
                            {
                                "kind": "raw_string",
                                "regex": "'s3://[^']+'",
                                **self._follows_s3_bucket_any_kind(),
                            },
                            # Has an S3 bucket followed by a
                            # concatenated S3 bucket (e.g. s3://$S3_BUCKET_NAME).
                            {
                                "kind": "concatenation",
                                "has": {
                                    "any": [
                                        {
                                            "kind": "word",
                                            "regex": "\\As3://",
                                        },
                                        {
                                            "kind": "string",
                                            "has": {
                                                "kind": "string_content",
                                                "nthChild": 1,
                                                "regex": "\\As3://",
                                            },
                                        },
                                        {
                                            "kind": "raw_string",
                                            "regex": "'s3://[^']+'",
                                        },
                                    ]
                                },
                                **self._follows_s3_bucket_any_kind(),
                            },
                        ]
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
