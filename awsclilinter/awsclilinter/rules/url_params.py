from typing import List

from ast_grep_py.ast_grep_py import SgRoot

from awsclilinter.rules import LintFinding, LintRule


class UrlParamsRule(LintRule):
    """Detects AWS CLI ECR get-login commands."""

    _SUGGESTED_MANUAL_FIX = (
        "If you need to retrieve a URL and pass the URL contents into a parameter value, "
        "we recommend that you use curl or a similar tool to download the contents of the URL "
        "to a local file. Then, use the file:// syntax to read the contents of that file and use "
        "it as the parameter value. See https://docs.aws.amazon.com/cli/latest/userguide/"
        "cliv2-migration-changes.html#cliv2-migration-paramfile.\n"
    )

    @property
    def name(self) -> str:
        return "url-params"

    @property
    def description(self) -> str:
        return (
            "For input parameters that have a prefix of http:// or https://, AWS CLI v2 will not "
            "automatically request the content of the URL for the parameter, and the "
            "`cli_follow_urlparam` option has been removed. See "
            "https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html"
            "#cliv2-migration-paramfile.\n"
        )

    def check(self, root: SgRoot) -> List[LintFinding]:
        """Check for AWS CLI commands with URL parameters."""
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
                {"any": [
                    # Unquoted URL argument
                    {
                        "has": {
                            "kind": "word",
                            "regex": "\\A(http://|https://)",
                            # Don't detect the URL parameter if it is the value of --endpoint-url.
                            "not": {
                                "follows": {
                                    "kind": "word",
                                    "pattern": "--endpoint-url",
                                }
                            }
                        }
                    },
                    # Double-quoted URL argument
                    {
                        "has": {
                            "kind": "string",
                            "has": {
                                "kind": "string_content",
                                "nthChild": 1,
                                "regex": "\\A(http://|https://)",
                            },
                            # Don't detect the URL parameter if it is the value of --endpoint-url.
                            "not": {
                                "follows": {
                                    "kind": "word",
                                    "pattern": "--endpoint-url",
                                }
                            }
                        }
                    },
                    # Raw-string URL argument
                    {
                        "has": {
                            "kind": "raw_string",
                            "regex": "\\A(http://|https://)",
                            # Don't detect the URL parameter if it is the value of --endpoint-url.
                            "not": {
                                "follows": {
                                    "kind": "word",
                                    "pattern": "--endpoint-url",
                                }
                            }
                        }
                    },
                    # Concatenated URL argument. We detect concatenation starting with
                    # any of the types: (1) unquoted string (2) double-quoted string
                    # (3) raw string.
                    {
                        "has": {
                            "kind": "concatenation",
                            "any": [
                                {
                                    "has": {
                                        "kind": "word",
                                        "nthChild": 1,
                                        "regex": "\\A(http://|https://)",
                                    }
                                },
                                {
                                    "has": {
                                        "kind": "string",
                                        "nthChild": 1,
                                        "has": {
                                            "kind": "string_content",
                                            "nthChild": 1,
                                            "regex": "\\A(http://|https://)",
                                        }
                                    }
                                },
                                {
                                    "has": {
                                        "kind": "raw_string",
                                        "nthChild": 1,
                                        "regex": "\\A(http://|https://)",
                                    }
                                }
                            ],
                            # Don't detect the URL parameter if it is the value of --endpoint-url.
                            "not": {
                                "follows": {
                                    "kind": "word",
                                    "pattern": "--endpoint-url",
                                }
                            }
                        }
                    }
                ]},
                # Command is not ecr get-login, since it was replaced with ecr get-login-password
                # in AWS CLI v2. We don't want to guide users to migrate URL parameters to file
                # parameters since the replacement command does not take parameters at all.
                {"not": {"has": {"kind": "word", "pattern": "ecr"}}},
                {"not": {"has": {"kind": "word", "pattern": "get-login"}}},
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
