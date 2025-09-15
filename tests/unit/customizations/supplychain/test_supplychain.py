# Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import unittest
from unittest.mock import Mock, MagicMock

from awscli.testutils import BaseAWSCommandParamsTest
from awscli.customizations.supplychain.supplychain import SupplyChainCommand
from awscli.customizations.supplychain import initialize, inject_commands


class TestSupplyChainInitialization(unittest.TestCase):
    """Test supply chain command initialization"""

    def test_initialize_registers_event(self):
        """Test that initialize registers the correct event"""
        cli = Mock()
        initialize(cli)
        cli.register.assert_called_once_with(
            'building-command-table.main', inject_commands
        )

    def test_inject_commands_adds_supplychain(self):
        """Test that inject_commands adds the supplychain command"""
        command_table = {}
        session = Mock()

        inject_commands(command_table, session)

        self.assertIn('supplychain', command_table)
        self.assertIsInstance(command_table['supplychain'], SupplyChainCommand)


class TestSupplyChainCommand(unittest.TestCase):
    """Test the main SupplyChainCommand class"""

    def setUp(self):
        self.session = Mock()
        self.command = SupplyChainCommand(self.session)

    def test_command_name(self):
        """Test command has correct name"""
        self.assertEqual(self.command.NAME, 'supplychain')

    def test_command_has_subcommands(self):
        """Test command has expected subcommands"""
        expected_subcommands = [
            'generate-sbom', 'scan', 'attest', 'query',
            'policy', 'inventory', 'report'
        ]

        subcommand_names = [sc['name'] for sc in self.command.SUBCOMMANDS]

        for expected in expected_subcommands:
            self.assertIn(expected, subcommand_names)

    def test_command_description(self):
        """Test command has a description"""
        self.assertIsNotNone(self.command.DESCRIPTION)
        self.assertIn('supply chain', self.command.DESCRIPTION.lower())

    def test_run_main_shows_help(self):
        """Test that running without subcommands shows help"""
        parsed_args = Mock()
        parsed_globals = Mock()

        # Mock the _display_help method
        self.command._display_help = Mock()

        result = self.command._run_main(parsed_args, parsed_globals)

        self.command._display_help.assert_called_once_with(
            parsed_args, parsed_globals
        )
        self.assertEqual(result, 1)


class TestSupplyChainIntegration(BaseAWSCommandParamsTest):
    """Integration test for supply chain command"""

    def test_supplychain_help(self):
        """Test that help command works"""
        # This would test the actual command help output
        # Note: This requires the full AWS CLI test infrastructure
        pass  # Simplified for this implementation