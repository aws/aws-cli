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

_HIDDEN_ALIASES = [
    {
        "service": "cognito-identity",
        "operation": "create-identity-pool",
        "alternative": "open-id-connect-provider-arns",
        "alias": "open-id-connect-provider-ar-ns",
    },
    {
        "service": "storagegateway",
        "operation": "describe-tapes",
        "alternative": "tape-arns",
        "alias": "tape-ar-ns",
    },
    {
        "service": "storagegateway",
        "operation": "describe-tape-archives",
        "alternative": "tape-arns",
        "alias": "tape-ar-ns",
    },
    {
        "service": "storagegateway",
        "operation": "describe-vtl-devices",
        "alternative": "vtl-device-arns",
        "alias": "vtl-device-ar-ns",
    },
    {
        "service": "storagegateway",
        "operation": "describe-cached-iscsi-volumes",
        "alternative": "volume-arns",
        "alias": "volume-ar-ns",
    },
    {
        "service": "storagegateway",
        "operation": "describe-stored-iscsi-volumes",
        "alternative": "volume-arns",
        "alias": "volume-ar-ns",
    },
    {
        "service": "route53domains",
        "operation": "view-billing",
        "alternative": "start-time",
        "alias": "start",
    },
    {
        "service": "deploy",
        "operation": "create-deployment-group",
        "alternative": "ec2-tag-set",
        "alias": "ec-2-tag-set",
    },
    {
        "service": "deploy",
        "operation": "list-application-revisions",
        "alternative": "s3-bucket",
        "alias": "s-3-bucket",
    },
    {
        "service": "deploy",
        "operation": "list-application-revisions",
        "alternative": "s3-key-prefix",
        "alias": "s-3-key-prefix",
    },
    {
        "service": "deploy",
        "operation": "update-deployment-group",
        "alternative": "ec2-tag-set",
        "alias": "ec-2-tag-set",
    },
    {
        "service": "iam",
        "operation": "enable-mfa-device",
        "alternative": "authentication-code1",
        "alias": "authentication-code-1",
    },
    {
        "service": "iam",
        "operation": "enable-mfa-device",
        "alternative": "authentication-code2",
        "alias": "authentication-code-2",
    },
    {
        "service": "iam",
        "operation": "resync-mfa-device",
        "alternative": "authentication-code1",
        "alias": "authentication-code-1",
    },
    {
        "service": "iam",
        "operation": "resync-mfa-device",
        "alternative": "authentication-code2",
        "alias": "authentication-code-2",
    },
    {
        "service": "importexport",
        "operation": "get-shipping-label",
        "alternative": "street1",
        "alias": "street-1",
    },
    {
        "service": "importexport",
        "operation": "get-shipping-label",
        "alternative": "street2",
        "alias": "street-2",
    },
    {
        "service": "importexport",
        "operation": "get-shipping-label",
        "alternative": "street3",
        "alias": "street-3",
    },
    {
        "service": "lambda",
        "operation": "publish-version",
        "alternative": "code-sha256",
        "alias": "code-sha-256",
    },
    {
        "service": "lightsail",
        "operation": "import-key-pair",
        "alternative": "public-key-base64",
        "alias": "public-key-base-64",
    },
    {
        "service": "opsworks",
        "operation": "register-volume",
        "alternative": "ec2-volume-id",
        "alias": "ec-2-volume-id",
        "deprecated": True,
    },
]


class HiddenAliasRule(LintRule):
    """Detects AWS CLI commands using hidden aliases."""

    def __init__(
        self,
        alias: str,
        alternative: str,
        service: str,
        operation: str,
        deprecated: bool = False,
    ):
        self._hidden_alias = alias
        self._alternative = alternative
        self._service = service
        self._operation = operation
        self._deprecated = deprecated

    @property
    def name(self) -> str:
        return f"hidden-alias-{self._hidden_alias}"

    @property
    def description(self) -> str:
        return (
            (
                f"In AWS CLI v2, the hidden alias {self._hidden_alias} was removed. "
                "You must replace usage of the obsolete alias with the corresponding "
                f"working parameter: {self._alternative}. See "
                "https://docs.aws.amazon.com/cli/latest/userguide"
                "/cliv2-migration-changes.html#cliv2-migration-aliases."
            )
            if not self._deprecated
            else (
                f"In AWS CLI v2, The hidden alias {self._hidden_alias} was removed. "
                f"Additionally, the {self._service} service was deprecated and removed. See "
                "https://docs.aws.amazon.com/cli/latest/userguide"
                "/cliv2-migration-changes.html#cliv2-migration-aliases."
            )
        )

    def check(self, root: SgRoot) -> List[LintFinding]:
        """Check for AWS CLI commands using hidden aliases."""
        node = root.root()
        nodes = node.find_all(
            all=[  # type: ignore[arg-type]
                {"kind": "command"},
                has_aws_command_any_kind(),
                {
                    "has": {
                        "kind": "word",
                        "pattern": self._service,
                    }
                },
                {
                    "has": {
                        "kind": "word",
                        "pattern": self._operation,
                    }
                },
                # Has the hidden alias parameter (unquoted, double-quoted, or single-quoted).
                {
                    "has": {
                        "any": [
                            {
                                "kind": "word",
                                "pattern": f"--{self._hidden_alias}",
                            },
                            {
                                "kind": "string",
                                "pattern": f'"--{self._hidden_alias}"',
                            },
                            {"kind": "raw_string", "pattern": f"'--{self._hidden_alias}'"},
                        ]
                    }
                },
            ]
        )

        findings = []
        for stmt in nodes:
            original = stmt.text()
            suggested = original.replace(f"--{self._hidden_alias}", f"--{self._alternative}")
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


def create_all_hidden_alias_rules() -> List[HiddenAliasRule]:
    """Create and return a list of all hidden alias rules: one for each hidden alias
    removed in AWS CLI v2.
    """
    return [
        HiddenAliasRule(
            alias=hidden_alias_def["alias"],
            alternative=hidden_alias_def["alternative"],
            service=hidden_alias_def["service"],
            operation=hidden_alias_def["operation"],
            deprecated=hidden_alias_def.get("deprecated", False),
        )
        for hidden_alias_def in _HIDDEN_ALIASES
    ]
