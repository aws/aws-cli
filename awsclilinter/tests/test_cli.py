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
            assert "--cli-binary-format" in fixed_content

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
            assert "--cli-binary-format" in output_file.read_text()

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
            with patch("builtins.input", side_effect=["y", "y"]):
                main()
                fixed_content = output_file.read_text()
                assert fixed_content.count("--cli-binary-format") == 2

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
                assert fixed_content.count("--cli-binary-format") == 2

    def test_interactive_mode_cancel(self, tmp_path):
        """Test interactive mode with 'x' to cancel."""
        script_file = tmp_path / "test.sh"
        script_file.write_text(
            "aws secretsmanager put-secret-value --secret-id secret1213 --secret-binary file://data.json"
        )

        with patch("sys.argv", ["upgrade-aws-cli", "--script", str(script_file), "--interactive"]):
            with patch("builtins.input", return_value="q"):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0
