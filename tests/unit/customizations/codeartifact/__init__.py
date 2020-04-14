from awscli.testutils import unittest
from awscli.testutils import mock
from awscli.customizations.codeartifact import register_codeartifact_commands
from awscli.customizations.codeartifact import inject_commands
from awscli.customizations.codeartifact.login import CodeArtifactLogin


class TestRegisterCodeArtifactCommands(unittest.TestCase):
    def test_register_codeartifact_commands(self):
        event_emitter = mock.Mock()
        register_codeartifact_commands(event_emitter)
        event_emitter.register.assert_called_once_with(
            'building-command-table.codeartifact', inject_commands
        )


class TestInjectCommands(unittest.TestCase):
    def test_inject_commands(self):
        command_table = {}
        session = mock.Mock()
        inject_commands(command_table, session)
        self.assertIn('login', command_table)
        self.assertIsInstance(
            command_table['login'], CodeArtifactLogin
        )
