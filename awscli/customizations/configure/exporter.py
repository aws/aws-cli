import sys
import json
import os

sys.path.insert(0, 'D:/Repos GitKraken/aws-cli')
from awscli.customizations.commands import BasicCommand
from awscli.customizations.configure.writer import ConfigFileWriter

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
            raise RuntimeError('No credentials available. Try running "aws configure" first.')	
        try:
            with open('credentials.json', 'w') as f:
                json.dump(credentials.get_frozen_credentials(), f)
        except:
            raise RuntimeError('Failed while trying to export credentials. Check your permissions and try again.')