from awsclilinter.linter import ScriptLinter
from awsclilinter.rules.base64_rule import Base64BinaryFormatRule


class TestScriptLinter:
    """Test cases for ScriptLinter."""

    def test_lint_finds_issues(self):
        """Test that linter finds issues in script."""
        script = "aws secretsmanager put-secret-value --secret-id secret1213 --secret-binary file://data.json"
        linter = ScriptLinter([Base64BinaryFormatRule()])
        findings_with_rules = linter.lint(script)

        assert len(findings_with_rules) == 1
        finding, rule = findings_with_rules[0]
        assert finding.rule_name == "binary-params-base64"
        assert "aws" in finding.original_text

    def test_apply_fixes(self):
        """Test that fixes are applied correctly."""
        script = "aws secretsmanager put-secret-value --secret-id secret1213 --secret-binary file://data.json"
        linter = ScriptLinter([Base64BinaryFormatRule()])
        findings_with_rules = linter.lint(script)
        finding, _ = findings_with_rules[0]
        fixed = linter.apply_single_fix(script, finding)

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
        linter = ScriptLinter([Base64BinaryFormatRule()])
        findings_with_rules = linter.lint(script)

        # 2 commands, 1 rule = 2 findings
        assert len(findings_with_rules) == 2
