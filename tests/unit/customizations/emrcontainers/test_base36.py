# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.testutils import unittest
from awscli.customizations.emrcontainers.base36 import Base36

class TestBase36(unittest.TestCase):
    base36 = Base36()

    # Use case: Provide various strings as input and assert that
    # base36 encoded string is correct
    # Expected results: Expected base36 encoded string is returned
    def test_base36_encoding(self):
        # Test for empty string
        self.assertEqual(self.base36.encode(''), '0')

        # Test for a short string
        self.assertEqual(self.base36.encode('abcdefghijkl'),
                         '2x6xx5ubcrus4bplmr0')

        # Test for a really lengthy string
        self.assertEqual(self.base36.encode('abcdefghijklmnopqrstuvwxyzabcdef'
                                            'ghijklmnopqrstuvwxyzabcdefghijkl'
                                            'mnopqrstuvwxyzabcdefghijklmnopqr'
                                            'stuvwxyzabcdefghijklmnopqrstuvwx'),
                         'hihg421ybq8vpwgxd21fae22r9rho7x8qpyskkz6iqadme7ds5f'
                         'qxpnedq44doj5dlitkm8wswo3c5503yl55jfazzhbbqnnee7r70'
                         'zw89fs5ojeipi6xeiydas7g7y9w3usdlzrlhxx0q50bxvt27tfu'
                         '3ruwyx4fuv96rcfpkqxxg93vdclsof5ribhnrcvajmpvc')

        # Test for a string with only special characters
        self.assertEqual(self.base36.encode('+=,.@-_'), '3bu5b0xg4tb')

        # Test for a string containing special characters
        self.assertEqual(self.base36.encode('abcdefghijkl+=,.@-_'),
                         '1ll75jdngh5gbk11wbh7h35ji05wtb')


if __name__ == "__main__":
    unittest.main()
