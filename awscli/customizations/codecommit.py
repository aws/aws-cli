# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import os
import re
import sys
import logging
import fileinput
import datetime

from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.compat import urlsplit
from awscli.customizations.commands import BasicCommand
from awscli.compat import NonTranslatedStdout

logger = logging.getLogger('botocore.credentials')


def initialize(cli):
    """
    The entry point for the credential helper
    """
    cli.register('building-command-table.codecommit', inject_commands)


def inject_commands(command_table, session, **kwargs):
    """
    Injects new commands into the codecommit subcommand.
    """
    command_table['credential-helper'] = CodeCommitCommand(session)


class CodeCommitNoOpStoreCommand(BasicCommand):
    NAME = 'store'
    DESCRIPTION = ('This operation does nothing, credentials'
                   ' are calculated each time')
    SYNOPSIS = ('aws codecommit credential-helper store')
    EXAMPLES = ''
    _UNDOCUMENTED = True

    def _run_main(self, args, parsed_globals):
        return 0


class CodeCommitNoOpEraseCommand(BasicCommand):
    NAME = 'erase'
    DESCRIPTION = ('This operation does nothing, no credentials'
                   ' are ever stored')
    SYNOPSIS = ('aws codecommit credential-helper erase')
    EXAMPLES = ''
    _UNDOCUMENTED = True

    def _run_main(self, args, parsed_globals):
        return 0


class CodeCommitGetCommand(BasicCommand):
    NAME = 'get'
    DESCRIPTION = ('get a username SigV4 credential pair'
                   ' based on protocol, host and path provided'
                   ' from standard in. This is primarily'
                   ' called by git to generate credentials to'
                   ' authenticate against AWS CodeCommit')
    SYNOPSIS = ('aws codecommit credential-helper get')
    EXAMPLES = (r'echo -e "protocol=https\\n'
                r'path=/v1/repos/myrepo\\n'
                'host=git-codecommit.us-east-1.amazonaws.com"'
                ' | aws codecommit credential-helper get')
    ARG_TABLE = [
        {
            'name': 'ignore-host-check',
            'action': 'store_true',
            'default': False,
            'group_name': 'ignore-host-check',
            'help_text': (
                'Optional. Generate credentials regardless of whether'
                ' the domain is an Amazon domain.'
                )
            }
        ]

    def __init__(self, session):
        super(CodeCommitGetCommand, self).__init__(session)

    def _run_main(self, args, parsed_globals):
        git_parameters = self.read_git_parameters()
        if ('amazon.com' in git_parameters['host'] or
                'amazonaws.com' in git_parameters['host'] or
                args.ignore_host_check):
            theUrl = self.extract_url(git_parameters)
            region = self.extract_region(git_parameters, parsed_globals)
            signature = self.sign_request(region, theUrl)
            self.write_git_parameters(signature)
        return 0

    def write_git_parameters(self, signature):
        username = self._session.get_credentials().access_key
        if self._session.get_credentials().token is not None:
            username += "%" + self._session.get_credentials().token
        # Python will add a \r to the line ending for a text stdout in Windows.
        # Git does not like the \r, so switch to binary
        with NonTranslatedStdout() as binary_stdout:
            binary_stdout.write('username={0}\n'.format(username))
            logger.debug('username\n%s', username)
            binary_stdout.write('password={0}\n'.format(signature))
            # need to explicitly flush the buffer here,
            # before we turn the stream back to text for windows
            binary_stdout.flush()
            logger.debug('signature\n%s', signature)

    def read_git_parameters(self):
        parsed = {}
        for line in sys.stdin:
            key, value = line.strip().split('=', 1)
            parsed[key] = value
        return parsed

    def extract_url(self, parameters):
        url = '{0}://{1}/{2}'.format(parameters['protocol'],
                                     parameters['host'],
                                     parameters['path'])
        return url

    def extract_region(self, parameters, parsed_globals):
        match = re.match(r'git-codecommit\.([^.]+)\.amazonaws\.com',
                         parameters['host'])
        if match is not None:
            return match.group(1)
        elif parsed_globals.region is not None:
            return parsed_globals.region
        else:
            return self._session.get_config_variable('region')

    def sign_request(self, region, url_to_sign):
        credentials = self._session.get_credentials()
        signer = SigV4Auth(credentials, 'codecommit', region)
        request = AWSRequest()
        request.url = url_to_sign
        request.method = 'GIT'
        now = datetime.datetime.utcnow()
        request.context['timestamp'] = now.strftime('%Y%m%dT%H%M%S')
        split = urlsplit(request.url)
        # we don't want to include the port number in the signature
        hostname = split.netloc.split(':')[0]
        canonical_request = '{0}\n{1}\n\nhost:{2}\n\nhost\n'.format(
            request.method,
            split.path,
            hostname)
        logger.debug("Calculating signature using v4 auth.")
        logger.debug('CanonicalRequest:\n%s', canonical_request)
        string_to_sign = signer.string_to_sign(request, canonical_request)
        logger.debug('StringToSign:\n%s', string_to_sign)
        signature = signer.signature(string_to_sign, request)
        logger.debug('Signature:\n%s', signature)
        return '{0}Z{1}'.format(request.context['timestamp'], signature)


class CodeCommitCommand(BasicCommand):
    NAME = 'credential-helper'
    SYNOPSIS = ('aws codecommit credential-helper')
    EXAMPLES = ''

    SUBCOMMANDS = [
        {'name': 'get', 'command_class': CodeCommitGetCommand},
        {'name': 'store', 'command_class': CodeCommitNoOpStoreCommand},
        {'name': 'erase', 'command_class': CodeCommitNoOpEraseCommand},
    ]
    DESCRIPTION = ('Provide a SigV4 compatible user name and'
                   ' password for git smart HTTP '
                   ' These commands are consumed by git and'
                   ' should not used directly. Erase and Store'
                   ' are no-ops. Get is operation to generate'
                   ' credentials to authenticate AWS CodeCommit.'
                   ' Run \"aws codecommit credential-helper help\"'
                   ' for details')

    def _run_main(self, args, parsed_globals):
        raise ValueError('usage: aws [options] codecommit'
                         ' credential-helper <subcommand> '
                         '[parameters]\naws: error: too few arguments')
