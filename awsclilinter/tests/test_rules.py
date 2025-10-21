from ast_grep_py import SgRoot

from awsclilinter.rules.base64_rule import Base64BinaryFormatRule


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
        assert "--cli-binary-format" in findings[0].suggested_fix

    def test_no_detection_with_flag(self):
        """Test no detection when flag is present."""
        script = "aws secretsmanager put-secret-value --secret-id secret1213 --secret-binary file://data.json --cli-binary-format raw-in-base64-out"
        root = SgRoot(script, "bash")
        rule = Base64BinaryFormatRule()
        findings = rule.check(root)

        assert len(findings) == 0

    def test_no_detection_without_file_protocol(self):
        """Test no detection when file:// is not used. Even though the breaking change may
        still occur without the use of file://, only the case where file:// is used can be detected
        statically."""
        script = "aws secretsmanager put-secret-value --secret-id secret1213 --secret-string secret123"
        root = SgRoot(script, "bash")
        rule = Base64BinaryFormatRule()
        findings = rule.check(root)

        assert len(findings) == 0
