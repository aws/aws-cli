from unittest.mock import patch

import pytest

from awsclilinter.cli import main


class TestCLI:
    """Test cases for CLI interface."""

    def test_script_not_found(self, capsys):
        """Test error when script file doesn't exist."""
        with patch("sys.argv", ["upgrade-aws-cli", "--script", "nonexistent.sh"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_fix_and_output_conflict(self, capsys):
        """Test error when both --fix and --output are provided."""
        with patch(
            "sys.argv", ["upgrade-aws-cli", "--script", "test.sh", "--fix", "--output", "out.sh"]
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_fix_and_interactive_conflict(self, capsys):
        """Test error when both --fix and --interactive are provided."""
        with patch(
            "sys.argv", ["upgrade-aws-cli", "--script", "test.sh", "--fix", "--interactive"]
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_no_issues_found(self, tmp_path, capsys):
        """Test output when no issues are found."""
        script_file = tmp_path / "test.sh"
        script_file.write_text("echo 'hello world'")

        with patch("sys.argv", ["upgrade-aws-cli", "--script", str(script_file)]):
            main()
            captured = capsys.readouterr()
            assert "No issues found" in captured.out

    def test_dry_run_mode(self, tmp_path, capsys):
        """Test dry run mode displays findings."""
        script_file = tmp_path / "test.sh"
        script_file.write_text(
            "aws secretsmanager put-secret-value --secret-id secret1213 --secret-binary file://data.json"
        )

        with patch("sys.argv", ["upgrade-aws-cli", "--script", str(script_file)]):
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

        with patch("sys.argv", ["upgrade-aws-cli", "--script", str(script_file), "--fix"]):
            main()
            fixed_content = script_file.read_text()
            # 1 command, 2 rules = 2 flags added
            assert "--cli-binary-format" in fixed_content
            assert "--no-cli-pager" in fixed_content

    def test_output_mode(self, tmp_path):
        """Test output mode creates new file."""
        script_file = tmp_path / "test.sh"
        output_file = tmp_path / "output.sh"
        script_file.write_text(
            "aws secretsmanager put-secret-value --secret-id secret1213 --secret-binary file://data.json"
        )

        with patch(
            "sys.argv",
            ["upgrade-aws-cli", "--script", str(script_file), "--output", str(output_file)],
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
                "upgrade-aws-cli",
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

        with patch("sys.argv", ["upgrade-aws-cli", "--script", str(script_file), "--interactive"]):
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
                "upgrade-aws-cli",
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
                "upgrade-aws-cli",
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
                "upgrade-aws-cli",
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
