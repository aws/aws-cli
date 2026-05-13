# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import pytest

from awscli.lazy import LazyCommand
from awscli.testutils import mock


class TestLazyCommandErrorPaths:
    def test_invalid_module_path_raises_on_resolve(self):
        session = mock.MagicMock()
        cmd = LazyCommand(
            'bad-cmd',
            session,
            'awscli.nonexistent.module',
            'FakeCommand',
        )
        with pytest.raises(ModuleNotFoundError):
            cmd([], mock.MagicMock())

    def test_invalid_class_name_raises_on_resolve(self):
        session = mock.MagicMock()
        cmd = LazyCommand(
            'bad-cmd',
            session,
            'awscli.customizations.dynamodb.ddb',
            'NonexistentClass',
        )
        with pytest.raises(AttributeError):
            cmd([], mock.MagicMock())

    def test_invalid_module_path_raises_on_help(self):
        session = mock.MagicMock()
        cmd = LazyCommand(
            'bad-cmd',
            session,
            'awscli.nonexistent.module',
            'FakeCommand',
        )
        with pytest.raises(ModuleNotFoundError):
            cmd.create_help_command()
