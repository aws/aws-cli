from awscli.testutils import unittest
from awscli.customizations.history.filters import RegexFilter


class TestRegexFilter(unittest.TestCase):
    def assert_filter(self, pattern, replacement, input_text,
                      expected_result):
        regex_filter = RegexFilter(pattern, replacement)
        result = regex_filter.filter_text(input_text)
        self.assertEqual(result, expected_result)

    def test_can_filter_out_content(self):
        self.assert_filter(
            pattern='foo',
            replacement='bar',
            input_text='Content with foo.',
            expected_result='Content with bar.',
        )

    def test_can_filter_with_backreferences(self):
        self.assert_filter(
            pattern='Key=(....).*',
            replacement=r'Key=\1...',
            input_text='Key=foobar',
            expected_result='Key=foob...',
        )

    def test_does_not_filter_if_no_match(self):
        self.assert_filter(
            pattern='Key=(....).*',
            replacement=r'Key=\1...',
            input_text='Blah=foobar',
            expected_result='Blah=foobar',
        )
