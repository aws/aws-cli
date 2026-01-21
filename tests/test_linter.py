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
from aws_cli_migrate import linter
from aws_cli_migrate.rules.binary_params_base64 import Base64BinaryFormatRule
from aws_cli_migrate.rules.ecr_get_login import EcrGetLoginRule


class TestLinter:
    """Test cases for linter functions."""

    def test_lint_finds_issues(self):
        """Test that linter finds issues in script."""
        script = "aws secretsmanager put-secret-value --secret-id secret1213 --secret-binary file://data.json"
        ast = linter.parse(script)
        findings_with_rules = linter.lint(ast, [Base64BinaryFormatRule()])

        assert len(findings_with_rules) == 1
        finding, rule = findings_with_rules[0]
        assert finding.rule_name == "binary-params-base64"
        assert "aws" in finding.original_text

    def test_apply_fixes(self):
        """Test that fixes are applied correctly."""
        script = "aws secretsmanager put-secret-value --secret-id secret1213 --secret-binary file://data.json"
        ast = linter.parse(script)
        findings_with_rules = linter.lint(ast, [Base64BinaryFormatRule()])
        findings = [f for f, _ in findings_with_rules]
        fixed = linter.apply_fixes(ast, findings)

        assert "--cli-binary-format raw-in-base64-out" in fixed
        assert "file://data.json" in fixed

    def test_multiple_issues(self):
        """Test linter with multiple issues."""
        script = (
            "aws secretsmanager put-secret-value --secret-id secret1213 "
            "--secret-binary file://data.json\n"
            "            aws kinesis put-record --stream-name samplestream "
            "--data file://data --partition-key samplepartitionkey"
        )
        ast = linter.parse(script)
        findings_with_rules = linter.lint(ast, [Base64BinaryFormatRule()])

        # 2 commands, 1 rule = 2 findings
        assert len(findings_with_rules) == 2

    def test_manual_review_findings(self):
        """Test that linter handles manual review findings correctly."""
        script = "aws ecr get-login --region us-west-2"
        ast = linter.parse(script)
        findings_with_rules = linter.lint(ast, [EcrGetLoginRule()])

        assert len(findings_with_rules) == 1
        finding, rule = findings_with_rules[0]
        assert finding.rule_name == "ecr-get-login"
        assert finding.edit is None
        assert finding.auto_fixable is False

    def test_apply_fixes_skips_manual_review(self):
        """Test that apply_fixes skips non-fixable findings."""
        script = "aws ecr get-login --region us-west-2"
        ast = linter.parse(script)
        findings_with_rules = linter.lint(ast, [EcrGetLoginRule()])
        findings = [f for f, _ in findings_with_rules]
        fixed = linter.apply_fixes(ast, findings)

        # Script should be unchanged since finding is not auto-fixable
        assert fixed == script

    def test_mixed_fixable_and_manual_review(self):
        """Test linter with both fixable and manual review findings."""
        script = (
            "aws secretsmanager put-secret-value --secret-id secret1213 --secret-binary file://data.json\n"
            "aws ecr get-login --region us-west-2"
        )
        ast = linter.parse(script)
        findings_with_rules = linter.lint(ast, [Base64BinaryFormatRule(), EcrGetLoginRule()])

        assert len(findings_with_rules) == 2

        # First finding should be fixable
        fixable_finding = findings_with_rules[0][0]
        assert fixable_finding.auto_fixable is True
        assert fixable_finding.edit is not None

        # Second finding should be manual review
        manual_finding = findings_with_rules[1][0]
        assert manual_finding.auto_fixable is False
        assert manual_finding.edit is None

        # Apply fixes should only fix the fixable finding
        findings = [f for f, _ in findings_with_rules]
        fixed = linter.apply_fixes(ast, findings)
        assert "--cli-binary-format" in fixed
        assert "aws ecr get-login" in fixed  # Manual review command unchanged
