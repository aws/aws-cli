# Copyright 2012-2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

from argparse import Namespace

from awscli.customizations.servicecatalog import GenerateCommand
from awscli.customizations.exceptions import ParamValidationError
from awscli.testutils import unittest


class TestGenerateCommand(unittest.TestCase):
    def setUp(self):
        self.cmd = GenerateCommand(None)

    def test_no_subcommand(self):
        # Arrange
        arguments = Namespace()
        arguments.subcommand = None

        # Act+Assert
        with self.assertRaises(ParamValidationError):
            self.cmd._run_main(arguments, None)

    def test_with_subcommand(self):
        # Arrange
        arguments = Namespace(subcommand="product")

        # Act
        self.cmd._run_main(arguments, None)
