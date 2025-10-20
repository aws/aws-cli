from ast_grep_py import SgRoot

from awsclilinter.rules.base64_rule import Base64BinaryFormatRule


class TestBase64BinaryFormatRule:
    """Test cases for Base64BinaryFormatRule."""

    def test_rule_properties(self):
        """Test rule name and description."""
        rule = Base64BinaryFormatRule()
        assert rule.name == "base64-binary-format"
        assert "cli-binary-format" in rule.description

    def test_detects_missing_flag(self):
        """Test detection of missing --cli-binary-format flag."""
        script = "aws s3api put-object --bucket mybucket --body file://data.json"
        root = SgRoot(script, "bash")
        rule = Base64BinaryFormatRule()
        findings = rule.check(root)

        assert len(findings) == 1
        assert "--cli-binary-format" in findings[0].suggested_fix

    def test_no_detection_with_flag(self):
        """Test no detection when flag is present."""
        script = "aws s3api put-object --bucket mybucket --body file://data.json --cli-binary-format raw-in-base64-out"
        root = SgRoot(script, "bash")
        rule = Base64BinaryFormatRule()
        findings = rule.check(root)

        assert len(findings) == 0

    def test_no_detection_without_file_protocol(self):
        """Test no detection when file:// is not used."""
        script = "aws s3api put-object --bucket mybucket --body data.json"
        root = SgRoot(script, "bash")
        rule = Base64BinaryFormatRule()
        findings = rule.check(root)

        assert len(findings) == 0
