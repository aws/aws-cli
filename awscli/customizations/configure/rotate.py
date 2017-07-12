# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import os
import sys

from awscli.customizations.commands import BasicCommand
from awscli.customizations.configure.writer import ConfigFileWriter

from . import PREDEFINED_SECTION_NAMES


class ConfigureRotateCommand(BasicCommand):
    NAME = 'rotate'
    DESCRIPTION = BasicCommand.FROM_FILE('configure', 'rotate-access-key',
                                         '_description.rst')
    SYNOPSIS = 'aws [--profile profile-name] configure rotate-access-key'
    EXAMPLES = BasicCommand.FROM_FILE('configure', 'rotate-access-key', '_examples.rst')
    ARG_TABLE = [
    ]
    # Any variables specified in this list will be written to
    # the ~/.aws/credentials file instead of ~/.aws/config.
    _WRITE_TO_CREDS_FILE = ['aws_access_key_id', 'aws_secret_access_key',
                            'aws_session_token']

    def __init__(self, session, config_writer=None, stream=sys.stdout):
        super(ConfigureRotateCommand, self).__init__(session)
        self._stream = stream
        if config_writer is None:
            config_writer = ConfigFileWriter()
        self._config_writer = config_writer

    def _run_main(self, args, parsed_globals):
        self._stream.write('Try to rotate %s\n' % (self._session.get_credentials().access_key,))
        self.iam = self._session.create_client('iam')
        keys = self.iam.list_access_keys()
        access_key = None
        other_key = None
        for _key in keys['AccessKeyMetadata']:
            if _key['AccessKeyId'] == self._session.get_credentials().access_key:
                access_key = _key
            else:
                other_key = _key
        if len(keys['AccessKeyMetadata']) > 1:
            self._stream.write('Cannot rotate key %s as another key exists %s\n' % (
                    self._session.get_credentials().access_key, other_key['AccessKeyId']))
            return
        if not access_key:
            self._stream.write('Cannot find key %s\n' % (self._session.get_credentials().access_key,))
            return
        new_key = self.iam.create_access_key(UserName=access_key['UserName'])['AccessKey']
        self._update(new_key['AccessKeyId'], new_key['SecretAccessKey'])
        self.iam.delete_access_key(UserName=access_key['UserName'], AccessKeyId=access_key['AccessKeyId'])
        self._stream.write('New key is %s\n' % (new_key['AccessKeyId'],))

    def _update(self, access_key_id, secret):
        section = 'default'
        if self._session.profile is not None:
            section = 'profile %s' % self._session.profile
        updated_config = {'__section__': section, 'aws_access_key_id': access_key_id, 'aws_secret_access_key': secret}
        config_filename = os.path.expanduser(self._session.get_config_variable('credentials_file'))
        section_name = updated_config['__section__']
        if section_name.startswith('profile '):
            updated_config['__section__'] = section_name[8:]
        self._config_writer.update_config(updated_config, config_filename)
