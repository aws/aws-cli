# Copyright (c) 2013 Amazon.com, Inc. or its affiliates.  All Rights Reserved
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
import unittest

from awscli.table import Section, MultiTable, convert_to_vertical_table


class TestSection(unittest.TestCase):
    def setUp(self):
        self.section = Section()

    def test_add_row_tracks_max_widths(self):
        self.section.add_row(['one', 'two', 'three'])
        self.assertEqual(self.section.calculate_column_widths(), [3, 3, 5])
        self.section.add_row(['1234567', '1234567', '1234567'])
        self.assertEqual(self.section.calculate_column_widths(), [7, 7, 7])
        self.section.add_row(['a', 'a', 'a'])
        self.assertEqual(self.section.calculate_column_widths(), [7, 7, 7])
        self.section.add_row(['123456789', '1', '1'])
        self.assertEqual(self.section.calculate_column_widths(), [9, 7, 7])
        self.assertEqual(self.section.calculate_column_widths(1), [10, 8, 8])
        self.assertEqual(self.section.total_width(), 23)

    def test_add_row_also_tracks_header(self):
        self.section.add_header(['123456789', '12345', '1234567'])
        self.section.add_row(['a', 'a', 'a'])
        self.section.add_row(['aa', 'aa', 'aa'])
        self.section.add_row(['aaa', 'aaa', 'aaa'])
        self.assertEqual(self.section.calculate_column_widths(), [9, 5, 7])
        self.assertEqual(self.section.total_width(), 21)
        self.section.add_row(['aaa', '123456789', 'aaa'])
        self.assertEqual(self.section.calculate_column_widths(), [9, 9, 7])
        self.assertEqual(self.section.total_width(padding=3, with_border=True),
                         36)

    def test_max_width_with_scaling_perfect_scaling(self):
        self.section.add_row(['one', 'two', 'three'])
        self.section.add_row(['1234567', '1234567', '1234567'])
        # Perfect scaling, exactly double.
        widths = self.section.calculate_column_widths(max_width=42)
        self.assertEqual(widths, [14, 14, 14])

    def test_max_width_scaling_one_unit_short(self):
        self.section.add_row(['one', 'two', 'three'])
        self.section.add_row(['1234567', '1234567', '1234567'])
        widths = self.section.calculate_column_widths(max_width=41)
        self.assertEqual(widths, [13, 14, 14])

    def test_max_width_scaling_is_negative(self):
        self.section.add_row(['12345', '12345'])
        widths = self.section.calculate_column_widths(max_width=17)
        self.assertEqual(widths, [8, 9])

    def test_allow_sections_to_be_padded(self):
        self.section.add_row(['one', 'two', 'three'])
        self.section.add_row(['1234567', '1234567', '1234567'])
        self.assertEqual(self.section.total_width(padding=2), 27)
        self.assertEqual(
            self.section.total_width(padding=2, outer_padding=1), 29)

    def test_title_accounts_for_outer_padding(self):
        self.section.add_row(['a', 'b', 'c'])
        self.section.add_title('123456789')
        self.assertEqual(
            self.section.total_width(padding=2, outer_padding=3), 17)

    def test_unicode_text_row(self):
        self.section.add_row([1])
        self.section.add_row(['check'])
        self.section.add_row([u'\u2713'])
        self.assertEqual(
            self.section.rows,
            [[u'1'], [u'check'], [u'\u2713']])


class TestMultiTable(unittest.TestCase):
    def setUp(self):
        self.table = MultiTable()

    def test_max_width_calculation(self):
        self.table.add_title('foo')
        self.table.add_row_header(['one', 'two', 'three'])
        self.table.add_row(['one', 'two', 'three'])
        self.table.new_section('bar')
        self.table.add_row_header(['one', 'two'])
        self.table.add_row(['12345', '1234567'])


class TestVerticalTableConversion(unittest.TestCase):
    def setUp(self):
        self.table = MultiTable()

    def test_convert_section_to_vertical(self):
        self.table.add_title('foo')
        self.table.add_row_header(['key1', 'key2', 'key3'])
        self.table.add_row(['val1', 'val2', 'val3'])
        convert_to_vertical_table(self.table._sections)
        # To convert to a vertical table, there should be no headers:
        section = self.table._sections[0]
        self.assertEqual(section.headers, [])
        # Then we should create a two column row with key val pairs.
        self.assertEqual(
            section.rows,
            [['key1', 'val1'], ['key2', 'val2'], ['key3', 'val3']])


if __name__ == '__main__':
    unittest.main()
