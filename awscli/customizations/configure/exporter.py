from awscli.customizations.configure.writer import ConfigFileWriter
from awscli.customizations.commands import BasicCommand
from awscli.customizations.utils import uni_print
import sys
import json
import os


class ConfigureExportCommand(BasicCommand):
    NAME = 'export-credentials'
    DESCRIPTION = 'Exports the AWS credentials used with the command "aws configure" to a the config file.'
    EXAMPLES = 'aws configure export-credentials'

    def __init__(self, session):
        super(ConfigureExportCommand, self).__init__(session)

    def _run_main(self, parsed_args, parsed_globals):
        self.export_credentials(self._session)
        return 0

    def export_credentials(self, session):
        """
        Exports the AWS credentials used with the command 'aws configure' to a file.
        """
        credentials = session.get_credentials()
        if credentials is None:
            raise RuntimeError(
                'No credentials available. Try running "aws configure" first.')
        try:
            credentials_data = credentials.get_frozen_credentials()
            dump = {'aws_access_key_id': credentials_data.access_key,
                    'aws_secret_access_key': credentials_data.secret_key}
            if credentials_data.token is not None:
                dump['aws_session_token'] = credentials_data.token
            uni_print(json.dumps(dump, indent=4))
        except:
            raise RuntimeError(
                'Failed while trying to export credentials. Check your permissions and try again.')
