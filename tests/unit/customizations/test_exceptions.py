# -*- coding: utf-8 -*-
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
import io

from botocore.exceptions import NoCredentialsError

from awscli.testutils import unittest, mock
from awscli.customizations.exceptions import ExceptionHandler


class FakeException(Exception):
    RC = 222
    DEBUG_MESSAGE = 'dummy message'


class FakeBotocoreException(NoCredentialsError):
    fmt = 'error message'


class TestExceptionHandler(unittest.TestCase):

    def test_can_handle_exception_with_rc(self):
        stderr = io.StringIO()
        with mock.patch("sys.stderr", stderr):
            with ExceptionHandler(Exception) as error:
                raise FakeException('critical error')
        self.assertEqual(error.rc, 222)
        self.assertEqual(stderr.getvalue().strip(), 'critical error')

    def test_can_handle_exception_wo_rc(self):
        stderr = io.StringIO()
        with mock.patch("sys.stderr", stderr):
            with ExceptionHandler(Exception) as error:
                raise Exception('critical error')
        self.assertEqual(error.rc, 255)
        self.assertEqual(stderr.getvalue().strip(), 'critical error')

    def test_can_handle_botocore_exception(self):
        stderr = io.StringIO()
        with mock.patch("sys.stderr", stderr):
            with ExceptionHandler(Exception) as error:
                raise FakeBotocoreException
        self.assertEqual(error.rc, 253)
        self.assertEqual(stderr.getvalue().strip(),
                         'error message. You can configure '
                         'credentials by running "aws configure".')
