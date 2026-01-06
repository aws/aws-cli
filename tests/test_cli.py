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
from unittest.mock import patch

import pytest

from aws_cli_migrate.cli import main


class TestCLI:
    """Test cases for CLI interface."""

    def test_script_not_found(self, capsys):
        """Test error when script file doesn't exist."""
        with patch("sys.argv", ["migrate-aws-cli", "--script", "nonexistent.sh"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_fix_and_output_conflict(self, capsys):
        """Test error when both --fix and --output are provided."""
        with patch(
            "sys.argv", ["migrate-aws-cli", "--script", "test.sh", "--fix", "--output", "out.sh"]
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_fix_and_interactive_conflict(self, capsys):
        """Test error when both --fix and --interactive are provided."""
        with patch(
            "sys.argv", ["migrate-aws-cli", "--script", "test.sh", "--fix", "--interactive"]
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_no_issues_found(self, tmp_path, capsys):
        """Test output when no issues are found."""
        script_file = tmp_path / "test.sh"
        script_file.write_text("echo 'hello world'")

        with patch("sys.argv", ["migrate-aws-cli", "--script", str(script_file)]):
            main()
            captured = capsys.readouterr()
            assert "No issues found" in captured.out

    def test_dry_run_mode(self, tmp_path, capsys):
        """Test dry run mode displays findings."""
        script_file = tmp_path / "test.sh"
        script_file.write_text(
            "aws secretsmanager put-secret-value --secret-id secret1213 --secret-binary file://data.json"
        )

        with patch("sys.argv", ["migrate-aws-cli", "--script", str(script_file)]):
            main()
            captured = capsys.readouterr()
            assert "Found" in captured.out
            assert "issue" in captured.out

    def test_fix_mode(self, tmp_path):
        """Test fix mode modifies the script."""
        script_file = tmp_path / "test.sh"
        script_file.write_text(
            "aws secretsmanager put-secret-value --secret-id secret1213 --secret-binary file://data.json"
        )

        with patch("sys.argv", ["migrate-aws-cli", "--script", str(script_file), "--fix"]):
            main()
            fixed_content = script_file.read_text()
            # 1 command, 2 rules = 2 flags added
            assert "--cli-binary-format" in fixed_content
            assert "--no-cli-pager" in fixed_content

    def test_fix_mode_multiple_lint_rules_per_command(self, tmp_path, capsys):
        """Test fix mode in the case that multiple linting rules have findings
        for a single command.
        """
        script_file = tmp_path / "test.sh"
        script_file.write_text(
            "aws lambda publish-version --function-name myfunction --code-sha256 abc123\n"
            "aws deploy create-deployment-group --application-name myapp "
            "--deployment-group-name mygroup --ec-2-tag-set file://tags.json"
        )

        with patch("sys.argv", ["migrate-aws-cli", "--script", str(script_file), "--fix"]):
            main()
            captured = capsys.readouterr()

            # Should show fix was applied
            assert "Applied 5 fix(es) automatically" in captured.out
            # The number of lines should remain the same after applying fixes
            assert len(script_file.read_text().splitlines()) == 2

            # The hidden alias must not be present in the modified script
            assert "--ec-2-tag-set" not in script_file.read_text()

            # The no-pager flag should appear twice in the modified script, one for each command.
            assert script_file.read_text().count("--no-cli-pager") == 2

    def test_output_mode(self, tmp_path):
        """Test output mode creates new file."""
        script_file = tmp_path / "test.sh"
        output_file = tmp_path / "output.sh"
        script_file.write_text(
            "aws secretsmanager put-secret-value --secret-id secret1213 --secret-binary file://data.json"
        )

        with patch(
            "sys.argv",
            ["migrate-aws-cli", "--script", str(script_file), "--output", str(output_file)],
        ):
            main()
            assert output_file.exists()
            content = output_file.read_text()
            # 1 command, 2 rules = 2 flags added
            assert "--cli-binary-format" in content
            assert "--no-cli-pager" in content

    def test_interactive_mode_accept_all(self, tmp_path):
        """Test interactive mode with 'y' to accept all changes."""
        script_file = tmp_path / "test.sh"
        output_file = tmp_path / "output.sh"
        script_file.write_text(
            "aws secretsmanager put-secret-value --secret-id secret1213 --secret-binary file://data.json\n"
            "aws kinesis put-record --stream-name samplestream --data file://data "
            "--partition-key samplepartitionkey"
        )

        with patch(
            "sys.argv",
            [
                "migrate-aws-cli",
                "--script",
                str(script_file),
                "--interactive",
                "--output",
                str(output_file),
            ],
        ):
            with patch("builtins.input", side_effect=["y", "y", "y", "y"]):
                main()
                fixed_content = output_file.read_text()
                print(fixed_content)
                # 2 commands, 2 rules = 4 findings, so 2 of each flag
                assert fixed_content.count("--cli-binary-format") == 2
                assert fixed_content.count("--no-cli-pager") == 2

    def test_interactive_mode_reject_all(self, tmp_path, capsys):
        """Test interactive mode with 'n' to reject all changes."""
        script_file = tmp_path / "test.sh"
        original = "aws secretsmanager put-secret-value --secret-id secret1213 --secret-binary file://data.json"
        script_file.write_text(original)

        with patch("sys.argv", ["migrate-aws-cli", "--script", str(script_file), "--interactive"]):
            with patch("builtins.input", return_value="n"):
                main()
                captured = capsys.readouterr()
                assert "No changes accepted" in captured.out

    def test_interactive_mode_update_all(self, tmp_path):
        """Test interactive mode with 'u' to accept remaining changes."""
        script_file = tmp_path / "test.sh"
        output_file = tmp_path / "output.sh"
        script_file.write_text(
            "aws secretsmanager put-secret-value --secret-id secret1213 --secret-binary file://data.json\n"
            "aws kinesis put-record --stream-name samplestream --data file://data "
            "--partition-key samplepartitionkey"
        )

        with patch(
            "sys.argv",
            [
                "migrate-aws-cli",
                "--script",
                str(script_file),
                "--interactive",
                "--output",
                str(output_file),
            ],
        ):
            with patch("builtins.input", return_value="u"):
                main()
                fixed_content = output_file.read_text()
                # 2 commands, 2 rules = 4 findings, so 2 of each flag
                assert fixed_content.count("--cli-binary-format") == 2
                assert fixed_content.count("--no-cli-pager") == 2

    def test_interactive_mode_save_and_exit(self, tmp_path):
        """Test interactive mode with 's' to save and exit."""
        script_file = tmp_path / "test.sh"
        output_file = tmp_path / "output.sh"
        script_file.write_text(
            "aws secretsmanager put-secret-value --secret-id secret1213 --secret-binary file://data.json\n"
            "aws kinesis put-record --stream-name samplestream --data file://data "
            "--partition-key samplepartitionkey"
        )

        with patch(
            "sys.argv",
            [
                "migrate-aws-cli",
                "--script",
                str(script_file),
                "--interactive",
                "--output",
                str(output_file),
            ],
        ):
            with patch("builtins.input", side_effect=["y", "s"]):
                main()
                fixed_content = output_file.read_text()
                # Only first change should be applied since we pressed 's' on the second
                # First finding is binary-params-base64 for cmd1
                assert "--cli-binary-format" in fixed_content
                assert fixed_content.count("--cli-binary-format") == 1

    def test_interactive_mode_quit(self, tmp_path):
        """Test interactive mode with 'q' to quit without saving."""
        script_file = tmp_path / "test.sh"
        output_file = tmp_path / "output.sh"
        script_file.write_text(
            "aws secretsmanager put-secret-value --secret-id secret1213 --secret-binary file://data.json"
        )

        with patch(
            "sys.argv",
            [
                "migrate-aws-cli",
                "--script",
                str(script_file),
                "--interactive",
                "--output",
                str(output_file),
            ],
        ):
            with patch("builtins.input", return_value="q"):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0
                # Output file should not exist since we quit without saving
                assert not output_file.exists()

    def test_dry_run_mode_with_manual_review(self, tmp_path, capsys):
        """Test dry run mode displays manual review findings."""
        script_file = tmp_path / "test.sh"
        script_file.write_text("aws ecr get-login --region us-west-2")

        with patch("sys.argv", ["migrate-aws-cli", "--script", str(script_file)]):
            main()
            captured = capsys.readouterr()
            assert "MANUAL REVIEW REQUIRED" in captured.out
            assert "This issue requires manual intervention" in captured.out
            assert "get-login-password" in captured.out

    def test_fix_mode_with_manual_review(self, tmp_path, capsys):
        """Test fix mode displays manual review findings after applying fixes."""
        script_file = tmp_path / "test.sh"
        script_file.write_text(
            "aws secretsmanager put-secret-value --secret-id secret1213 --secret-binary file://data.json\n"
            "aws ecr get-login --region us-west-2"
        )

        with patch("sys.argv", ["migrate-aws-cli", "--script", str(script_file), "--fix"]):
            main()
            captured = capsys.readouterr()

            # Should show fix was applied
            assert "Applied 2 fix(es) automatically" in captured.out

            # Should show manual review section
            assert "issue(s) require manual review" in captured.out
            assert "MANUAL REVIEW REQUIRED" in captured.out
            assert "This issue requires manual intervention" in captured.out

            # Script should have auto-fixes applied but manual review command unchanged
            fixed_content = script_file.read_text()
            assert "--cli-binary-format" in fixed_content
            assert "--no-cli-pager" in fixed_content
            assert "aws ecr get-login" in fixed_content

    def test_interactive_mode_with_manual_review(self, tmp_path, capsys):
        """Test interactive mode handles manual review findings."""
        script_file = tmp_path / "test.sh"
        output_file = tmp_path / "output.sh"
        script_file.write_text(
            "aws secretsmanager put-secret-value --secret-id secret1213 --secret-binary file://data.json\n"
            "aws ecr get-login --region us-west-2"
        )

        with patch(
            "sys.argv",
            [
                "migrate-aws-cli",
                "--script",
                str(script_file),
                "--interactive",
                "--output",
                str(output_file),
            ],
        ):
            # Accept first two auto-fixable findings, then 'n' for manual review finding
            with patch("builtins.input", side_effect=["y", "y", "n"]):
                main()
                captured = capsys.readouterr()

                # Should display manual review finding
                assert "MANUAL REVIEW REQUIRED" in captured.out
                assert "This issue requires manual intervention" in captured.out

                # Should prompt with [n]ext, [s]ave and exit, [q]uit for manual review
                # (not [y]es, [n]o, [u]pdate all, etc.)

                # Output should have auto-fixes but not manual review changes
                fixed_content = output_file.read_text()
                assert "--cli-binary-format" in fixed_content
                assert "--no-cli-pager" in fixed_content
                assert "aws ecr get-login" in fixed_content

    def test_interactive_mode_manual_review_save_and_exit(self, tmp_path):
        """Test interactive mode with 's' on manual review finding."""
        script_file = tmp_path / "test.sh"
        output_file = tmp_path / "output.sh"
        script_file.write_text(
            "aws secretsmanager put-secret-value --secret-id secret1213 --secret-binary file://data.json\n"
            "aws ecr get-login --region us-west-2\n"
            "aws kinesis put-record --stream-name samplestream "
            "--data file://data --partition-key samplepartitionkey"
        )

        with patch(
            "sys.argv",
            [
                "migrate-aws-cli",
                "--script",
                str(script_file),
                "--interactive",
                "--output",
                str(output_file),
            ],
        ):
            # Accept all 4 auto-fixable findings, then 's' on manual review finding (5th)
            # This should save and exit without processing any remaining findings
            with patch("builtins.input", side_effect=["y", "y", "y", "y", "s"]):
                main()

                # Output should have all auto-fixes applied
                fixed_content = output_file.read_text()
                assert fixed_content.count("--cli-binary-format") == 2
                assert fixed_content.count("--no-cli-pager") == 2

                # Manual review command should be unchanged
                assert "aws ecr get-login" in fixed_content

                # Should have saved and exited
                assert output_file.exists()

    def test_version_flag(self, capsys):
        """Test --version flag displays version and exits."""
        with patch("sys.argv", ["migrate-aws-cli", "--version"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            captured = capsys.readouterr()
            assert "migrate-aws-cli" in captured.out

    def test_version_flag_short(self, capsys):
        """Test -v flag displays version and exits."""
        with patch("sys.argv", ["migrate-aws-cli", "-v"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0
            captured = capsys.readouterr()
            assert "migrate-aws-cli" in captured.out

    def test_non_aws_command_not_matched(self, tmp_path, capsys):
        """Test that commands like 'myaws' are not matched as AWS CLI commands."""
        script_file = tmp_path / "test.sh"
        script_file.write_text("'myaws' s3 ls")

        with patch("sys.argv", ["migrate-aws-cli", "--script", str(script_file)]):
            main()
            captured = capsys.readouterr()
            assert "No issues found" in captured.out

    def test_quoted_aws_command_matched(self, tmp_path, capsys):
        """Test that 'aws' in single quotes is correctly matched."""
        script_file = tmp_path / "test.sh"
        script_file.write_text(
            "'aws' secretsmanager put-secret-value --secret-id secret1213 --secret-binary file://data.json"
        )

        with patch("sys.argv", ["migrate-aws-cli", "--script", str(script_file)]):
            main()
            captured = capsys.readouterr()
            # Should find issues since 'aws' is a valid AWS CLI command
            assert "Found 2 issue" in captured.out
