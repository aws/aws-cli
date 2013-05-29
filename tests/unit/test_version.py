# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from tests import unittest
import os
import sys

from subprocess import Popen, PIPE

AWS_CMD = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))), 'bin', 'aws')


class TestVersion(unittest.TestCase):

    def test_session_can_be_passed_in(self):
        process = Popen(['python', AWS_CMD, '--version'], stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        stderr = stderr.decode('utf-8')
        self.assertTrue(stderr.startswith('aws-cli'), stderr)


if __name__ == '__main__':
    unittest.main()
