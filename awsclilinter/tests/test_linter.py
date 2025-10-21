from awsclilinter.linter import ScriptLinter
from awsclilinter.rules.base64_rule import Base64BinaryFormatRule


class TestScriptLinter:
    """Test cases for ScriptLinter."""

    def test_lint_finds_issues(self):
        """Test that linter finds issues in script."""
        script = "aws s3api put-object --bucket mybucket --key mykey --body file://data.json"
        linter = ScriptLinter([Base64BinaryFormatRule()])
        findings = linter.lint(script)

        assert len(findings) == 1
        assert findings[0].rule_name == "binary-params-base64"
        assert "file://" in findings[0].original_text

    def test_lint_no_issues(self):
        """Test that linter returns no findings for compliant script."""
        script = "aws s3api put-object --bucket mybucket --key mykey --body file://data.json --cli-binary-format raw-in-base64-out"
        linter = ScriptLinter([Base64BinaryFormatRule()])
        findings = linter.lint(script)

        assert len(findings) == 0

    def test_apply_fixes(self):
        """Test that fixes are applied correctly."""
        script = "aws s3api put-object --bucket mybucket --key mykey --body file://data.json"
        linter = ScriptLinter([Base64BinaryFormatRule()])
        findings = linter.lint(script)
        fixed = linter.apply_fixes(script, findings)

        assert "--cli-binary-format raw-in-base64-out" in fixed
        assert "file://data.json" in fixed

    def test_multiple_issues(self):
        """Test linter with multiple issues."""
        script = """aws s3api put-object --bucket mybucket --key mykey --body file://data.json
aws dynamodb put-item --table-name mytable --item file://item.json"""
        linter = ScriptLinter([Base64BinaryFormatRule()])
        findings = linter.lint(script)

        assert len(findings) == 2
