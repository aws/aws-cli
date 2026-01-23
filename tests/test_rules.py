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
from ast_grep_py.ast_grep_py import SgRoot

from aws_cli_migrate.rules.binary_params_base64 import Base64BinaryFormatRule
from aws_cli_migrate.rules.cli_input_json import CLIInputJSONRule
from aws_cli_migrate.rules.default_pager import DefaultPagerRule
from aws_cli_migrate.rules.deploy_empty_changeset import DeployEmptyChangesetRule
from aws_cli_migrate.rules.ecr_get_login import EcrGetLoginRule
from aws_cli_migrate.rules.hidden_aliases import HiddenAliasRule
from aws_cli_migrate.rules.s3_copies import S3CopyRule


class TestBase64BinaryFormatRule:
    """Test cases for Base64BinaryFormatRule."""

    def test_rule_properties(self):
        """Test rule description."""
        rule = Base64BinaryFormatRule()
        assert "cli-binary-format" in rule.description

    def test_detects_missing_flag(self):
        """Test detection of missing --cli-binary-format flag."""
        script = "aws secretsmanager put-secret-value --secret-id secret1213 --secret-binary file://data.json"
        root = SgRoot(script, "bash")
        rule = Base64BinaryFormatRule()
        findings = rule.check(root)

        assert len(findings) == 1
        assert "--cli-binary-format" in findings[0].edit.inserted_text

    def test_no_detection_with_flag(self):
        """Test no detection when flag is present."""
        script = (
            "aws secretsmanager put-secret-value --secret-id secret1213 "
            "--secret-binary file://data.json --cli-binary-format raw-in-base64-out"
        )
        root = SgRoot(script, "bash")
        rule = Base64BinaryFormatRule()
        findings = rule.check(root)

        assert len(findings) == 0

    def test_detects_ecr_describe_repositories(self):
        """Test detection for ecr describe-repositories command."""
        script = "aws ecr describe-repositories"
        root = SgRoot(script, "bash")
        rule = Base64BinaryFormatRule()
        findings = rule.check(root)

        assert len(findings) == 1
        assert "--cli-binary-format" in findings[0].edit.inserted_text


class TestDefaultPagerRule:
    """Test cases for DefaultPagerRule."""

    def test_rule_properties(self):
        """Test rule description."""
        rule = DefaultPagerRule()
        assert "pager" in rule.description

    def test_detects_missing_flag(self):
        """Test detection of missing --no-cli-pager flag."""
        script = "aws s3 ls s3://my-bucket"
        root = SgRoot(script, "bash")
        rule = DefaultPagerRule()
        findings = rule.check(root)

        assert len(findings) == 1
        assert "--no-cli-pager" in findings[0].edit.inserted_text

    def test_no_detection_with_flag(self):
        """Test no detection when flag is present."""
        script = "aws s3 ls s3://my-bucket --no-cli-pager"
        root = SgRoot(script, "bash")
        rule = DefaultPagerRule()
        findings = rule.check(root)

        assert len(findings) == 0

    def test_detects_multiple_commands(self):
        """Test detection across multiple commands."""
        script = "aws ec2 describe-instances\naws s3 ls"
        root = SgRoot(script, "bash")
        rule = DefaultPagerRule()
        findings = rule.check(root)

        assert len(findings) == 2

    def test_detects_ecr_describe_repositories(self):
        """Test detection for ecr describe-repositories command."""
        script = "aws ecr describe-repositories"
        root = SgRoot(script, "bash")
        rule = DefaultPagerRule()
        findings = rule.check(root)

        assert len(findings) == 1
        assert "--no-cli-pager" in findings[0].edit.inserted_text


class TestDeployEmptyChangesetRule:
    """Test cases for DeployEmptyChangesetRule."""

    def test_rule_properties(self):
        """Test rule description."""
        rule = DeployEmptyChangesetRule()
        assert "changeset" in rule.description

    def test_detects_missing_flag(self):
        """Test detection of missing --fail-on-empty-changeset flag."""
        script = "aws cloudformation deploy --template-file template.yaml --stack-name my-stack"
        root = SgRoot(script, "bash")
        rule = DeployEmptyChangesetRule()
        findings = rule.check(root)

        assert len(findings) == 1
        assert "--fail-on-empty-changeset" in findings[0].edit.inserted_text

    def test_no_detection_with_fail_flag(self):
        """Test no detection when --fail-on-empty-changeset is present."""
        script = "aws cloudformation deploy --template-file template.yaml --fail-on-empty-changeset"
        root = SgRoot(script, "bash")
        rule = DeployEmptyChangesetRule()
        findings = rule.check(root)

        assert len(findings) == 0

    def test_no_detection_with_no_fail_flag(self):
        """Test no detection when --no-fail-on-empty-changeset is present."""
        script = (
            "aws cloudformation deploy --template-file template.yaml --no-fail-on-empty-changeset"
        )
        root = SgRoot(script, "bash")
        rule = DeployEmptyChangesetRule()
        findings = rule.check(root)

        assert len(findings) == 0


class TestS3CopyRule:
    """Test cases for S3CopyRule."""

    def test_rule_properties(self):
        """Test rule description."""
        rule = S3CopyRule()
        assert "copy" in rule.description.lower()

    def test_detects_s3_cp_bucket_to_bucket(self):
        """Test detection of s3 cp bucket-to-bucket without --copy-props."""
        script = "aws s3 cp s3://source-bucket/file.txt s3://dest-bucket/file.txt"
        root = SgRoot(script, "bash")
        rule = S3CopyRule()
        findings = rule.check(root)

        assert len(findings) == 1
        assert "--copy-props none" in findings[0].edit.inserted_text

    def test_detects_s3_mv_bucket_to_bucket(self):
        """Test detection of s3 mv bucket-to-bucket without --copy-props."""
        script = "aws s3 mv s3://source-bucket/file.txt s3://dest-bucket/file.txt"
        root = SgRoot(script, "bash")
        rule = S3CopyRule()
        findings = rule.check(root)

        assert len(findings) == 1

    def test_detects_s3_sync_bucket_to_bucket(self):
        """Test detection of s3 sync bucket-to-bucket without --copy-props."""
        script = "aws s3 sync s3://source-bucket s3://dest-bucket"
        root = SgRoot(script, "bash")
        rule = S3CopyRule()
        findings = rule.check(root)

        assert len(findings) == 1

    def test_no_detection_with_copy_props(self):
        """Test no detection when --copy-props is present."""
        script = "aws s3 cp s3://source-bucket/file.txt s3://dest-bucket/file.txt --copy-props none"
        root = SgRoot(script, "bash")
        rule = S3CopyRule()
        findings = rule.check(root)

        assert len(findings) == 0

    def test_no_detection_local_to_s3(self):
        """Test no detection for local to s3 copy."""
        script = "aws s3 cp file.txt s3://dest-bucket/file.txt"
        root = SgRoot(script, "bash")
        rule = S3CopyRule()
        findings = rule.check(root)

        assert len(findings) == 0

    def test_no_detection_non_s3_paths(self):
        """Test no detection for paths that don't start with s3://."""
        script = "aws s3 cp 'as3://test-bucket1' 'as3://test-bucket2'"
        root = SgRoot(script, "bash")
        rule = S3CopyRule()
        findings = rule.check(root)

        assert len(findings) == 0


class TestHiddenAliasRule:
    """Test cases for HiddenAliasRule."""

    def test_rule_properties(self):
        """Test rule description."""
        rule = HiddenAliasRule(
            "authentication-code-1", "authentication-code1", "iam", "enable-mfa-device"
        )
        assert "authentication-code-1" in rule.description
        assert "authentication-code1" in rule.description

    def test_detects_hidden_alias(self):
        """Test detection of hidden alias usage."""
        script = "aws iam enable-mfa-device --user-name Bob --authentication-code-1 123456"
        root = SgRoot(script, "bash")
        rule = HiddenAliasRule(
            "authentication-code-1", "authentication-code1", "iam", "enable-mfa-device"
        )
        findings = rule.check(root)

        assert len(findings) == 1
        assert "--authentication-code1" in findings[0].edit.inserted_text

    def test_no_detection_with_correct_param(self):
        """Test no detection when correct parameter is used."""
        script = "aws iam enable-mfa-device --user-name Bob --authentication-code1 123456"
        root = SgRoot(script, "bash")
        rule = HiddenAliasRule(
            "authentication-code-1", "authentication-code1", "iam", "enable-mfa-device"
        )
        findings = rule.check(root)

        assert len(findings) == 0

    def test_detects_different_service_alias(self):
        """Test detection of alias in different service."""
        script = "aws lambda publish-version --function-name my-func --code-sha-256 abc123"
        root = SgRoot(script, "bash")
        rule = HiddenAliasRule("code-sha-256", "code-sha256", "lambda", "publish-version")
        findings = rule.check(root)

        assert len(findings) == 1
        assert "--code-sha256" in findings[0].edit.inserted_text

    def test_fix_replaces_hidden_alias(self):
        """Test detection of public-key-base-64 alias in lightsail."""
        script = (
            "aws lightsail import-key-pair --key-pair-name mykey --public-key-base-64 c3NoLXJzYQ=="
        )
        root = SgRoot(script, "bash")
        rule = HiddenAliasRule(
            "public-key-base-64", "public-key-base64", "lightsail", "import-key-pair"
        )
        findings = rule.check(root)

        assert len(findings) == 1
        assert "public-key-base-64" not in findings[0].edit.inserted_text
        assert "--public-key-base64" in findings[0].edit.inserted_text


class TestEcrGetLoginRule:
    """Test cases for EcrGetLoginRule (manual review only)."""

    def test_rule_properties(self):
        """Test rule description and auto_fixable property."""
        rule = EcrGetLoginRule()
        assert "ecr get-login" in rule.description

    def test_detects_ecr_get_login(self):
        """Test detection of ecr get-login command."""
        script = "aws ecr get-login --region us-west-2"
        root = SgRoot(script, "bash")
        rule = EcrGetLoginRule()
        findings = rule.check(root)

        assert len(findings) == 1
        assert findings[0].edit is None
        assert findings[0].auto_fixable is False

    def test_detects_ecr_get_login_with_debug(self):
        """Test detection of ecr get-login with --debug flag."""
        script = "aws ecr --debug get-login"
        root = SgRoot(script, "bash")
        rule = EcrGetLoginRule()
        findings = rule.check(root)

        assert len(findings) == 1
        assert findings[0].edit is None
        assert findings[0].auto_fixable is False

    def test_no_detection_for_other_ecr_commands(self):
        """Test no detection for other ECR commands."""
        script = "aws ecr describe-repositories"
        root = SgRoot(script, "bash")
        rule = EcrGetLoginRule()
        findings = rule.check(root)

        assert len(findings) == 0

    def test_detects_multiple_ecr_get_login(self):
        """Test detection of multiple ecr get-login commands."""
        script = "aws ecr get-login\naws ecr get-login --region us-east-1"
        root = SgRoot(script, "bash")
        rule = EcrGetLoginRule()
        findings = rule.check(root)

        assert len(findings) == 2
        for finding in findings:
            assert finding.edit is None
            assert finding.auto_fixable is False


class TestCLIInputJSONRule:
    """Test cases for CLIInputJSONRule (manual review only)."""

    def test_rule_properties(self):
        """Test rule description and auto_fixable property."""
        rule = CLIInputJSONRule()
        assert "cli-input-json" in rule.description
        assert "pagination" in rule.description

    def test_detects_cli_input_json(self):
        """Test detection of the `--cli-input-json` parameter."""
        script = "aws ec2 describe-instances --cli-input-json file://input.json"
        root = SgRoot(script, "bash")
        rule = CLIInputJSONRule()
        findings = rule.check(root)

        assert len(findings) == 1
        assert findings[0].edit is None
        assert findings[0].auto_fixable is False

    def test_detects_cli_input_json_double_quoted(self):
        """Test detection of the `--cli-input-json` parameter with double quotes."""
        script = 'aws s3api list-objects "--cli-input-json" file://input.json'
        root = SgRoot(script, "bash")
        rule = CLIInputJSONRule()
        findings = rule.check(root)

        assert len(findings) == 1
        assert findings[0].edit is None
        assert findings[0].auto_fixable is False

    def test_detects_cli_input_json_single_quoted(self):
        """Test detection of the `--cli-input-json` parameter with single quotes."""
        script = "aws dynamodb query '--cli-input-json' file://query.json"
        root = SgRoot(script, "bash")
        rule = CLIInputJSONRule()
        findings = rule.check(root)

        assert len(findings) == 1
        assert findings[0].edit is None
        assert findings[0].auto_fixable is False

    def test_no_detection_without_cli_input_json(self):
        """Test no detection when the `--cli-input-json` parameter is not present."""
        script = "aws ec2 describe-instances --region us-west-2"
        root = SgRoot(script, "bash")
        rule = CLIInputJSONRule()
        findings = rule.check(root)

        assert len(findings) == 0

    def test_detects_multiple_cli_input_json(self):
        """Test detection of multiple commands with --cli-input-json."""
        script = (
            "aws ec2 describe-instances --cli-input-json file://input.json\n"
            "aws s3api list-buckets --cli-input-json file://buckets.json"
        )
        root = SgRoot(script, "bash")
        rule = CLIInputJSONRule()
        findings = rule.check(root)

        assert len(findings) == 2
        for finding in findings:
            assert finding.edit is None
            assert finding.auto_fixable is False
