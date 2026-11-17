# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from unittest import mock

import pytest

from tests.utils.s3transfer import (
    requires_crt,
    skip_if_using_serial_implementation,
    skip_if_windows,
)


class TestSkipIfWindows:
    def test_bare_skip_if_windows_fails_immediately(self):
        with pytest.raises(TypeError):

            @skip_if_windows
            def my_test():
                pass

    def test_skip_if_windows_skips_on_windows(self):
        with mock.patch('tests.utils.s3transfer.platform') as mock_platform:
            mock_platform.system.return_value = 'Windows'

            @skip_if_windows('Not supported on Windows')
            def my_test():
                assert False

            assert getattr(my_test, '__unittest_skip__', False) is True

    def test_skip_if_windows_runs_on_non_windows(self):
        with mock.patch('tests.utils.s3transfer.platform') as mock_platform:
            mock_platform.system.return_value = 'Linux'

            @skip_if_windows('Not supported on Windows')
            def my_test():
                pass

            assert getattr(my_test, '__unittest_skip__', False) is False


class TestSkipIfUsingSerialImplementation:
    def test_bare_skip_if_using_serial_implementation_fails_immediately(self):
        with pytest.raises(TypeError):

            @skip_if_using_serial_implementation
            def my_test():
                pass

    def test_skip_if_using_serial_implementation_skips_when_serial(self):
        with mock.patch(
            'tests.utils.s3transfer.is_serial_implementation',
            return_value=True,
        ):

            @skip_if_using_serial_implementation(
                'Not supported in serial mode'
            )
            def my_test():
                assert False

            assert getattr(my_test, '__unittest_skip__', False) is True

    def test_skip_if_using_serial_implementation_runs_when_not_serial(self):
        with mock.patch(
            'tests.utils.s3transfer.is_serial_implementation',
            return_value=False,
        ):

            @skip_if_using_serial_implementation(
                'Not supported in serial mode'
            )
            def my_test():
                pass

            assert getattr(my_test, '__unittest_skip__', False) is False


class TestRequiresCrt:
    def test_bare_requires_crt_fails_immediately(self):
        with pytest.raises(TypeError):

            @requires_crt
            def my_test():
                pass

    def test_requires_crt_skips_when_no_crt(self):
        with mock.patch('tests.utils.s3transfer.HAS_CRT', False):

            @requires_crt()
            def my_test():
                assert False

            assert getattr(my_test, '__unittest_skip__', False) is True

    def test_requires_crt_runs_when_crt_available(self):
        with mock.patch('tests.utils.s3transfer.HAS_CRT', True):

            @requires_crt()
            def my_test():
                pass

            assert getattr(my_test, '__unittest_skip__', False) is False
