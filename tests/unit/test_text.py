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

import six
import mock

from awscli import text


class TestSection(unittest.TestCase):
    def format_text(self, data):
        stream = six.StringIO()
        text.format_text(data, stream=stream)
        return stream.getvalue()

    def assert_text_renders_to(self, data, expected_rendering):
        rendered = self.format_text(data)
        self.assertEqual(rendered, expected_rendering)

    def test_dict_format(self):
        self.assert_text_renders_to(dict(a=1, b=2, c=3), "1\t2\t3\n")

    def test_list_format(self):
        self.assert_text_renders_to([1, 2, 3], "1\t2\t3\n")

    def test_list_of_dicts(self):
        self.assert_text_renders_to(
            {'foo': [dict(a=1, b=2, c=3), dict(a=4, b=5, c=6)]},
            'FOO\t1\t2\t3\n'
            'FOO\t4\t5\t6\n')

    def test_multiple_list_of_dicts(self):
        self.assert_text_renders_to(
            {'foo': [dict(a=1, b=2, c=3), dict(a=4, b=5, c=6)],
             'zoo': [dict(a=7, b=8, c=9), dict(a=0, b=1, c=2)]},
            'FOO\t1\t2\t3\n'
            'FOO\t4\t5\t6\n'
            'ZOO\t7\t8\t9\n'
            'ZOO\t0\t1\t2\n'
        )


if __name__ == '__main__':
    unittest.main()
