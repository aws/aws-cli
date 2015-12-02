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
import os
import re
import sys
import logging

from botocore.exceptions import ProfileNotFound

from awscli.compat import raw_input
from awscli.customizations.commands import BasicCommand


logger = logging.getLogger(__name__)
NOT_SET = '<not set>'

PREDEFINED_SECTION_NAMES = ('preview', 'plugins')

def register_configure_cmd(cli):
    cli.register('building-command-table.main',
                 ConfigureCommand.add_command)


class ConfigValue(object):

    def __init__(self, value, config_type, config_variable):
        self.value = value
        self.config_type = config_type
        self.config_variable = config_variable

    def mask_value(self):
        if self.value is NOT_SET:
            return
        self.value = _mask_value(self.value)


class SectionNotFoundError(Exception):
    pass


def _mask_value(current_value):
    if current_value is None:
        return 'None'
    else:
        return ('*' * 16) + current_value[-4:]


class InteractivePrompter(object):

    def get_value(self, current_value, config_name, prompt_text=''):
        if config_name in ('aws_access_key_id', 'aws_secret_access_key'):
            current_value = _mask_value(current_value)
        response = raw_input("%s [%s]: " % (prompt_text, current_value))
        if not response:
            # If the user hits enter, we return a value of None
            # instead of an empty string.  That way we can determine
            # whether or not a value has changed.
            response = None
        return response


class ConfigFileWriter(object):
    SECTION_REGEX = re.compile(r'\[(?P<header>[^]]+)\]')
    OPTION_REGEX = re.compile(
        r'(?P<option>[^:=][^:=]*)'
        r'\s*(?P<vi>[:=])\s*'
        r'(?P<value>.*)$'
    )

    def update_config(self, new_values, config_filename):
        """Update config file with new values.

        This method will update a section in a config file with
        new key value pairs.

        This method provides a few conveniences:

        * If the ``config_filename`` does not exist, it will
          be created.  Any parent directories will also be created
          if necessary.
        * If the section to update does not exist, it will be created.
        * Any existing lines that are specified by ``new_values``
          **will not be touched**.  This ensures that commented out
          values are left unaltered.

        :type new_values: dict
        :param new_values: The values to update.  There is a special
            key ``__section__``, that specifies what section in the INI
            file to update.  If this key is not present, then the
            ``default`` section will be updated with the new values.

        :type config_filename: str
        :param config_filename: The config filename where values will be
            written.

        """
        section_name = new_values.pop('__section__', 'default')
        if not os.path.isfile(config_filename):
            self._create_file(config_filename)
            self._write_new_section(section_name, new_values, config_filename)
            return
        with open(config_filename, 'r') as f:
            contents = f.readlines()
        # We can only update a single section at a time so we first need
        # to find the section in question
        try:
            self._update_section_contents(contents, section_name, new_values)
            with open(config_filename, 'w') as f:
                f.write(''.join(contents))
        except SectionNotFoundError:
            self._write_new_section(section_name, new_values, config_filename)

    def _create_file(self, config_filename):
        # Create the file as well as the parent dir if needed.
        dirname = os.path.split(config_filename)[0]
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        with os.fdopen(os.open(config_filename,
                               os.O_WRONLY | os.O_CREAT, 0o600), 'w'):
            pass

    def _write_new_section(self, section_name, new_values, config_filename):
        with open(config_filename, 'a') as f:
            f.write('[%s]\n' % section_name)
            contents = []
            self._insert_new_values(line_number=0,
                                    contents=contents,
                                    new_values=new_values)
            f.write(''.join(contents))

    def _find_section_start(self, contents, section_name):
        for i in range(len(contents)):
            line = contents[i]
            if line.strip().startswith(('#', ';')):
                # This is a comment, so we can safely ignore this line.
                continue
            match = self.SECTION_REGEX.search(line)
            if match is not None and self._matches_section(match,
                                                           section_name):
                return i
        raise SectionNotFoundError(section_name)

    def _update_section_contents(self, contents, section_name, new_values):
        # First, find the line where the section_name is defined.
        # This will be the value of i.
        new_values = new_values.copy()
        # ``contents`` is a list of file line contents.
        section_start_line_num = self._find_section_start(contents,
                                                          section_name)
        # If we get here, then we've found the section.  We now need
        # to figure out if we're updating a value or adding a new value.
        # There's 2 cases.  Either we're setting a normal scalar value
        # of, we're setting a nested value.
        section_start_line_num += 1
        last_matching_line = section_start_line_num
        j = section_start_line_num
        while j < len(contents):
            line = contents[j]
            match = self.OPTION_REGEX.search(line)
            if match is not None:
                last_matching_line = j
                key_name = match.group(1).strip()
                if key_name in new_values:
                    # We've found the line that defines the option name.
                    # if the value is not a dict, then we can write the line
                    # out now.
                    if not isinstance(new_values[key_name], dict):
                        option_value = new_values[key_name]
                        new_line = '%s = %s\n' % (key_name, option_value)
                        contents[j] = new_line
                        del new_values[key_name]
                    else:
                        j = self._update_subattributes(
                            j, contents, new_values[key_name],
                            len(match.group(1)) - len(match.group(1).lstrip()))
                        return
            elif self.SECTION_REGEX.search(line) is not None:
                # We've hit a new section which means the config key is
                # not in the section.  We need to add it here.
                self._insert_new_values(line_number=last_matching_line,
                                        contents=contents,
                                        new_values=new_values)
                return
            j += 1

        if new_values:
            if not contents[-1].endswith('\n'):
                contents.append('\n')
            self._insert_new_values(line_number=last_matching_line + 1,
                                    contents=contents,
                                    new_values=new_values)

    def _update_subattributes(self, index, contents, values, starting_indent):
        index += 1
        for i in range(index, len(contents)):
            line = contents[i]
            match = self.OPTION_REGEX.search(line)
            if match is not None:
                current_indent = len(
                    match.group(1)) - len(match.group(1).lstrip())
                key_name = match.group(1).strip()
                if key_name in values:
                    option_value = values[key_name]
                    new_line = '%s%s = %s\n' % (' ' * current_indent,
                                                key_name, option_value)
                    contents[i] = new_line
                    del values[key_name]
            if starting_indent == current_indent or \
                    self.SECTION_REGEX.search(line) is not None:
                # We've arrived at the starting indent level so we can just
                # write out all the values now.
                self._insert_new_values(i - 1, contents, values, '    ')
                break
        else:
            if starting_indent != current_indent:
                # The option is the last option in the file
                self._insert_new_values(i, contents, values, '    ')
        return i

    def _insert_new_values(self, line_number, contents, new_values, indent=''):
        new_contents = []
        for key, value in list(new_values.items()):
            if isinstance(value, dict):
                subindent = indent + '    '
                new_contents.append('%s%s =\n' % (indent, key))
                for subkey, subval in list(value.items()):
                    new_contents.append('%s%s = %s\n' % (subindent, subkey,
                                                         subval))
            else:
                new_contents.append('%s%s = %s\n' % (indent, key, value))
            del new_values[key]
        contents.insert(line_number + 1, ''.join(new_contents))

    def _matches_section(self, match, section_name):
        parts = section_name.split(' ')
        unquoted_match = match.group(0) == '[%s]' % section_name
        if len(parts) > 1:
            quoted_match = match.group(0) == '[%s "%s"]' % (
                parts[0], ' '.join(parts[1:]))
            return unquoted_match or quoted_match
        return unquoted_match


class ConfigureListCommand(BasicCommand):
    NAME = 'list'
    DESCRIPTION = (
        'List the AWS CLI configuration data.  This command will '
        'show you the current configuration data.  For each configuration '
        'item, it will show you the value, where the configuration value '
        'was retrieved, and the configuration variable name.  For example, '
        'if you provide the AWS region in an environment variable, this '
        'command will show you the name of the region you\'ve configured, '
        'it will tell you that this value came from an environment '
        'variable, and it will tell you the name of the environment '
        'variable.\n'
    )
    SYNOPSIS = 'aws configure list [--profile profile-name]'
    EXAMPLES = (
        'To show your current configuration values::\n'
        '\n'
        '  $ aws configure list\n'
        '        Name                    Value             Type    Location\n'
        '        ----                    -----             ----    --------\n'
        '     profile                <not set>             None    None\n'
        '  access_key     ****************ABCD      config_file    ~/.aws/config\n'
        '  secret_key     ****************ABCD      config_file    ~/.aws/config\n'
        '      region                us-west-2              env    AWS_DEFAULT_REGION\n'
        '\n'
    )

    def __init__(self, session, stream=sys.stdout):
        super(ConfigureListCommand, self).__init__(session)
        self._stream = stream

    def _run_main(self, args, parsed_globals):
        self._display_config_value(ConfigValue('Value', 'Type', 'Location'),
                                   'Name')
        self._display_config_value(ConfigValue('-----', '----', '--------'),
                                   '----')

        if self._session.profile is not None:
            profile = ConfigValue(self._session.profile, 'manual',
                                  '--profile')
        else:
            profile = self._lookup_config('profile')
        self._display_config_value(profile, 'profile')

        access_key, secret_key = self._lookup_credentials()
        self._display_config_value(access_key, 'access_key')
        self._display_config_value(secret_key, 'secret_key')

        region = self._lookup_config('region')
        self._display_config_value(region, 'region')

    def _display_config_value(self, config_value, config_name):
        self._stream.write('%10s %24s %16s    %s\n' % (
            config_name, config_value.value, config_value.config_type,
            config_value.config_variable))

    def _lookup_credentials(self):
        # First try it with _lookup_config.  It's possible
        # that we don't find credentials this way (for example,
        # if we're using an IAM role).
        access_key = self._lookup_config('access_key')
        if access_key.value is not NOT_SET:
            secret_key = self._lookup_config('secret_key')
            access_key.mask_value()
            secret_key.mask_value()
            return access_key, secret_key
        else:
            # Otherwise we can try to use get_credentials().
            # This includes a few more lookup locations
            # (IAM roles, some of the legacy configs, etc.)
            credentials = self._session.get_credentials()
            if credentials is None:
                no_config = ConfigValue(NOT_SET, None, None)
                return no_config, no_config
            else:
                # For the ConfigValue, we don't track down the
                # config_variable because that info is not
                # visible from botocore.credentials.  I think
                # the credentials.method is sufficient to show
                # where the credentials are coming from.
                access_key = ConfigValue(credentials.access_key,
                                         credentials.method, '')
                secret_key = ConfigValue(credentials.secret_key,
                                         credentials.method, '')
                access_key.mask_value()
                secret_key.mask_value()
                return access_key, secret_key

    def _lookup_config(self, name):
        # First try to look up the variable in the env.
        value = self._session.get_config_variable(name, methods=('env',))
        if value is not None:
            return ConfigValue(value, 'env', self._session.session_var_map[name][1])
        # Then try to look up the variable in the config file.
        value = self._session.get_config_variable(name, methods=('config',))
        if value is not None:
            return ConfigValue(value, 'config-file',
                               self._session.get_config_variable('config_file'))
        else:
            return ConfigValue(NOT_SET, None, None)


class ConfigureSetCommand(BasicCommand):
    NAME = 'set'
    DESCRIPTION = BasicCommand.FROM_FILE('configure', 'set',
                                         '_description.rst')
    SYNOPSIS = 'aws configure set varname value [--profile profile-name]'
    EXAMPLES = BasicCommand.FROM_FILE('configure', 'set', '_examples.rst')
    ARG_TABLE = [
        {'name': 'varname',
         'help_text': 'The name of the config value to set.',
         'action': 'store',
         'cli_type_name': 'string', 'positional_arg': True},
        {'name': 'value',
         'help_text': 'The value to set.',
         'action': 'store',
         'cli_type_name': 'string', 'positional_arg': True},
    ]
    # Any variables specified in this list will be written to
    # the ~/.aws/credentials file instead of ~/.aws/config.
    _WRITE_TO_CREDS_FILE = ['aws_access_key_id', 'aws_secret_access_key',
                            'aws_session_token']

    def __init__(self, session, config_writer=None):
        super(ConfigureSetCommand, self).__init__(session)
        if config_writer is None:
            config_writer = ConfigFileWriter()
        self._config_writer = config_writer

    def _run_main(self, args, parsed_globals):
        varname = args.varname
        value = args.value
        section = 'default'
        # Before handing things off to the config writer,
        # we need to find out three things:
        # 1. What section we're writing to (section).
        # 2. The name of the config key (varname)
        # 3. The actual value (value).
        if '.' not in varname:
            # unqualified name, scope it to the current
            # profile (or leave it as the 'default' section if
            # no profile is set).
            if self._session.profile is not None:
                section = 'profile %s' % self._session.profile
        else:
            # First figure out if it's been scoped to a profile.
            parts = varname.split('.')
            if parts[0] in ('default', 'profile'):
                # Then we know we're scoped to a profile.
                if parts[0] == 'default':
                    section = 'default'
                    remaining = parts[1:]
                else:
                    # [profile, profile_name, ...]
                    section = "profile %s" % parts[1]
                    remaining = parts[2:]
                varname = remaining[0]
                if len(remaining) == 2:
                    value = {remaining[1]: value}
            elif parts[0] not in PREDEFINED_SECTION_NAMES:
                if self._session.profile is not None:
                    section = 'profile %s' % self._session.profile
                else:
                    profile_name = self._session.get_config_variable('profile')
                    if profile_name is not None:
                        section = profile_name
                varname = parts[0]
                if len(parts) == 2:
                    value = {parts[1]: value}
            elif len(parts) == 2:
                # Otherwise it's something like "set preview.service true"
                # of something in the [plugin] section.
                section, varname = parts
        config_filename = os.path.expanduser(
            self._session.get_config_variable('config_file'))
        updated_config = {'__section__': section, varname: value}
        if varname in self._WRITE_TO_CREDS_FILE:
            config_filename = os.path.expanduser(
                self._session.get_config_variable('credentials_file'))
            section_name = updated_config['__section__']
            if section_name.startswith('profile '):
                updated_config['__section__'] = section_name[8:]
        self._config_writer.update_config(updated_config, config_filename)


class ConfigureGetCommand(BasicCommand):
    NAME = 'get'
    DESCRIPTION = BasicCommand.FROM_FILE('configure', 'get',
                                         '_description.rst')
    SYNOPSIS = ('aws configure get varname [--profile profile-name]')
    EXAMPLES = BasicCommand.FROM_FILE('configure', 'get', '_examples.rst')
    ARG_TABLE = [
        {'name': 'varname',
         'help_text': 'The name of the config value to retrieve.',
         'action': 'store',
         'cli_type_name': 'string', 'positional_arg': True},
    ]

    def __init__(self, session, stream=sys.stdout):
        super(ConfigureGetCommand, self).__init__(session)
        self._stream = stream

    def _run_main(self, args, parsed_globals):
        varname = args.varname
        value = None
        if '.' not in varname:
            # get_scoped_config() returns the config variables in the config
            # file (not the logical_var names), which is what we want.
            config = self._session.get_scoped_config()
            value = config.get(varname)
        else:
            value = self._get_dotted_config_value(varname)
        if value is not None:
            self._stream.write(value)
            self._stream.write('\n')
            return 0
        else:
            return 1

    def _get_dotted_config_value(self, varname):
        parts = varname.split('.')
        num_dots = varname.count('.')
        # Logic to deal with predefined sections like [preview], [plugin] and etc.
        if num_dots == 1 and parts[0] in PREDEFINED_SECTION_NAMES:
            full_config = self._session.full_config
            section, config_name = varname.split('.')
            value = full_config.get(section, {}).get(config_name)
            if value is None:
                # Try to retrieve it from the profile config.
                value = full_config['profiles'].get(
                    section, {}).get(config_name)
            return value
        if parts[0] == 'profile':
            profile_name = parts[1]
            config_name = parts[2]
            remaining = parts[3:]
        # Check if varname starts with 'default' profile (e.g. default.emr-dev.emr.instance_profile)
        # If not, go further to check if varname starts with a known profile name
        elif parts[0] == 'default' or (parts[0] in self._session.full_config['profiles']):
            profile_name = parts[0]
            config_name = parts[1]
            remaining = parts[2:]
        else:
            profile_name = self._session.get_config_variable('profile')
            config_name = parts[0]
            remaining = parts[1:]

        value = self._session.full_config['profiles'].get(
            profile_name, {}).get(config_name)
        if len(remaining) == 1:
            try:
                value = value.get(remaining[-1])
            except AttributeError:
                value = None
        return value


class ConfigureCommand(BasicCommand):
    NAME = 'configure'
    DESCRIPTION = BasicCommand.FROM_FILE()
    SYNOPSIS = ('aws configure [--profile profile-name]')
    EXAMPLES = (
        'To create a new configuration::\n'
        '\n'
        '    $ aws configure\n'
        '    AWS Access Key ID [None]: accesskey\n'
        '    AWS Secret Access Key [None]: secretkey\n'
        '    Default region name [None]: us-west-2\n'
        '    Default output format [None]:\n'
        '\n'
        'To update just the region name::\n'
        '\n'
        '    $ aws configure\n'
        '    AWS Access Key ID [****]:\n'
        '    AWS Secret Access Key [****]:\n'
        '    Default region name [us-west-1]: us-west-2\n'
        '    Default output format [None]:\n'
    )
    SUBCOMMANDS = [
        {'name': 'list', 'command_class': ConfigureListCommand},
        {'name': 'get', 'command_class': ConfigureGetCommand},
        {'name': 'set', 'command_class': ConfigureSetCommand},
    ]

    # If you want to add new values to prompt, update this list here.
    VALUES_TO_PROMPT = [
        # (logical_name, config_name, prompt_text)
        ('aws_access_key_id', "AWS Access Key ID"),
        ('aws_secret_access_key', "AWS Secret Access Key"),
        ('region', "Default region name"),
        ('output', "Default output format"),
    ]

    def __init__(self, session, prompter=None, config_writer=None):
        super(ConfigureCommand, self).__init__(session)
        if prompter is None:
            prompter = InteractivePrompter()
        self._prompter = prompter
        if config_writer is None:
            config_writer = ConfigFileWriter()
        self._config_writer = config_writer

    def _run_main(self, parsed_args, parsed_globals):
        # Called when invoked with no args "aws configure"
        new_values = {}
        # This is the config from the config file scoped to a specific
        # profile.
        try:
            config = self._session.get_scoped_config()
        except ProfileNotFound:
            config = {}
        for config_name, prompt_text in self.VALUES_TO_PROMPT:
            current_value = config.get(config_name)
            new_value = self._prompter.get_value(current_value, config_name,
                                                 prompt_text)
            if new_value is not None and new_value != current_value:
                new_values[config_name] = new_value
        config_filename = os.path.expanduser(
            self._session.get_config_variable('config_file'))
        if new_values:
            self._write_out_creds_file_values(new_values,
                                              parsed_globals.profile)
            if parsed_globals.profile is not None:
                new_values['__section__'] = (
                    'profile %s' % parsed_globals.profile)
            self._config_writer.update_config(new_values, config_filename)

    def _write_out_creds_file_values(self, new_values, profile_name):
        # The access_key/secret_key are now *always* written to the shared
        # credentials file (~/.aws/credentials), see aws/aws-cli#847.
        # post-conditions: ~/.aws/credentials will have the updated credential
        # file values and new_values will have the cred vars removed.
        credential_file_values = {}
        if 'aws_access_key_id' in new_values:
            credential_file_values['aws_access_key_id'] = new_values.pop(
                'aws_access_key_id')
        if 'aws_secret_access_key' in new_values:
            credential_file_values['aws_secret_access_key'] = new_values.pop(
                'aws_secret_access_key')
        if credential_file_values:
            if profile_name is not None:
                credential_file_values['__section__'] = profile_name
            shared_credentials_filename = os.path.expanduser(
                self._session.get_config_variable('credentials_file'))
            self._config_writer.update_config(
                credential_file_values,
                shared_credentials_filename)
