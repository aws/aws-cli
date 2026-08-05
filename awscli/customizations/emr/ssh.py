# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import subprocess
import sys
import tempfile

from awscli.customizations.emr import constants
from awscli.customizations.emr import emrutils
from awscli.customizations.emr import sshutils
from awscli.customizations.emr.command import Command

KEY_PAIR_FILE_HELP_TEXT = '\nA value for the variable Key Pair File ' \
    'can be set in the AWS CLI config file using the ' \
    '"aws configure set emr.key_pair_file <value>" command.\n'

SSH_OPTIONS_HELP_TEXT = (
    'Additional SSH options passed directly to the ssh/scp command. '
    'Multiple options can be specified space-separated. Example: '
    '--ssh-options StrictHostKeyChecking=no ConnectTimeout=30')

DEFAULT_STRICT_HOST_KEY_CHECKING = 'StrictHostKeyChecking=accept-new'

UNSUPPORTED_OPTION_MSG = (
    'WARNING: Your OpenSSH version does not support '
    'StrictHostKeyChecking=accept-new (requires OpenSSH 7.6+). '
    'Falling back to StrictHostKeyChecking=no. '
    'Upgrade to OpenSSH 7.6+ for improved security.\n')

PUTTY_SSH_OPTIONS_MSG = (
    'WARNING: --ssh-options is only supported with OpenSSH. '
    'Options are ignored when using PuTTY/pscp.\n')


def _supports_accept_new():
    """Check if OpenSSH supports StrictHostKeyChecking=accept-new."""
    try:
        result = subprocess.run(
            ['ssh', '-G', '-o', 'StrictHostKeyChecking=accept-new',
             'localhost'],
            capture_output=True, text=True)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _has_strict_host_key_override(extra_options):
    """Check if user provided a StrictHostKeyChecking override."""
    if not extra_options:
        return False
    for opt in extra_options:
        if opt.lower().startswith('stricthostkeychecking='):
            return True
    return False


def _build_ssh_options(extra_options):
    """Build the -o flags list for ssh/scp commands."""
    options = []
    if _has_strict_host_key_override(extra_options):
        for opt in extra_options:
            options.extend(['-o', opt])
    else:
        if _supports_accept_new():
            options.extend(['-o', DEFAULT_STRICT_HOST_KEY_CHECKING])
        else:
            sys.stderr.write(UNSUPPORTED_OPTION_MSG)
            options.extend(['-o', 'StrictHostKeyChecking=no'])
        if extra_options:
            for opt in extra_options:
                options.extend(['-o', opt])
    return options


class Socks(Command):
    NAME = 'socks'
    DESCRIPTION = ('Create a socks tunnel on port 8157 from your machine '
                   'to the master.\n%s' % KEY_PAIR_FILE_HELP_TEXT)
    ARG_TABLE = [
        {'name': 'cluster-id', 'required': True,
         'help_text': 'Cluster Id of cluster you want to ssh into'},
        {'name': 'key-pair-file', 'required': True,
         'help_text': 'Private key file to use for login'},
        {'name': 'ssh-options', 'nargs': '+',
         'help_text': SSH_OPTIONS_HELP_TEXT},
    ]

    def _run_main_command(self, parsed_args, parsed_globals):
        try:
            master_dns = sshutils.validate_and_find_master_dns(
                session=self._session,
                parsed_globals=parsed_globals,
                cluster_id=parsed_args.cluster_id)

            key_file = parsed_args.key_pair_file
            sshutils.validate_ssh_with_key_file(key_file)
            f = tempfile.NamedTemporaryFile(delete=False)
            if (emrutils.which('ssh') or emrutils.which('ssh.exe')):
                ssh_options = _build_ssh_options(parsed_args.ssh_options)
                command = ['ssh'] + ssh_options + [
                    '-o', 'ServerAliveInterval=10', '-ND', '8157', '-i',
                    parsed_args.key_pair_file, constants.SSH_USER +
                    '@' + master_dns]
            else:
                if parsed_args.ssh_options:
                    sys.stderr.write(PUTTY_SSH_OPTIONS_MSG)
                command = ['putty', '-ssh', '-i', parsed_args.key_pair_file,
                           constants.SSH_USER + '@' + master_dns, '-N', '-D',
                           '8157']

            print(' '.join(command))
            rc = subprocess.call(command)
            return rc
        except KeyboardInterrupt:
            print('Disabling Socks Tunnel.')
            return 0


class SSH(Command):
    NAME = 'ssh'
    DESCRIPTION = ('SSH into master node of the cluster.\n%s' %
                   KEY_PAIR_FILE_HELP_TEXT)
    ARG_TABLE = [
        {'name': 'cluster-id', 'required': True,
         'help_text': 'Cluster Id of cluster you want to ssh into'},
        {'name': 'key-pair-file', 'required': True,
         'help_text': 'Private key file to use for login'},
        {'name': 'command', 'help_text': 'Command to execute on Master Node'},
        {'name': 'ssh-options', 'nargs': '+',
         'help_text': SSH_OPTIONS_HELP_TEXT},
    ]

    def _run_main_command(self, parsed_args, parsed_globals):
        master_dns = sshutils.validate_and_find_master_dns(
            session=self._session,
            parsed_globals=parsed_globals,
            cluster_id=parsed_args.cluster_id)

        key_file = parsed_args.key_pair_file
        sshutils.validate_ssh_with_key_file(key_file)
        f = tempfile.NamedTemporaryFile(delete=False)
        if (emrutils.which('ssh') or emrutils.which('ssh.exe')):
            ssh_options = _build_ssh_options(parsed_args.ssh_options)
            command = ['ssh'] + ssh_options + [
                '-o', 'ServerAliveInterval=10', '-i',
                parsed_args.key_pair_file, constants.SSH_USER +
                '@' + master_dns, '-t']
            if parsed_args.command:
                command.append(parsed_args.command)
        else:
            if parsed_args.ssh_options:
                sys.stderr.write(PUTTY_SSH_OPTIONS_MSG)
            command = ['putty', '-ssh', '-i', parsed_args.key_pair_file,
                       constants.SSH_USER + '@' + master_dns, '-t']
            if parsed_args.command:
                f.write(parsed_args.command)
                f.write('\nread -n1 -r -p "Command completed. Press any key."')
                command.append('-m')
                command.append(f.name)

        f.close()
        print(' '.join(command))
        rc = subprocess.call(command)
        os.remove(f.name)
        return rc


class Put(Command):
    NAME = 'put'
    DESCRIPTION = ('Put file onto the master node.\n%s' %
                   KEY_PAIR_FILE_HELP_TEXT)
    ARG_TABLE = [
        {'name': 'cluster-id', 'required': True,
         'help_text': 'Cluster Id of cluster you want to put file onto'},
        {'name': 'key-pair-file', 'required': True,
         'help_text': 'Private key file to use for login'},
        {'name': 'src', 'required': True,
         'help_text': 'Source file path on local machine'},
        {'name': 'dest', 'help_text': 'Destination file path on remote host'},
        {'name': 'ssh-options', 'nargs': '+',
         'help_text': SSH_OPTIONS_HELP_TEXT},
    ]

    def _run_main_command(self, parsed_args, parsed_globals):
        master_dns = sshutils.validate_and_find_master_dns(
            session=self._session,
            parsed_globals=parsed_globals,
            cluster_id=parsed_args.cluster_id)

        key_file = parsed_args.key_pair_file
        sshutils.validate_scp_with_key_file(key_file)
        if (emrutils.which('scp') or emrutils.which('scp.exe')):
            ssh_options = _build_ssh_options(parsed_args.ssh_options)
            command = ['scp', '-r'] + ssh_options + [
                '-i', parsed_args.key_pair_file, parsed_args.src,
                constants.SSH_USER + '@' + master_dns]
        else:
            if parsed_args.ssh_options:
                sys.stderr.write(PUTTY_SSH_OPTIONS_MSG)
            command = ['pscp', '-scp', '-r', '-i', parsed_args.key_pair_file,
                       parsed_args.src, constants.SSH_USER + '@' + master_dns]

        if parsed_args.dest:
            command[-1] = command[-1] + ":" + parsed_args.dest
        else:
            command[-1] = command[-1] + ":" + parsed_args.src.split('/')[-1]
        print(' '.join(command))
        rc = subprocess.call(command)
        return rc


class Get(Command):
    NAME = 'get'
    DESCRIPTION = ('Get file from master node.\n%s' % KEY_PAIR_FILE_HELP_TEXT)
    ARG_TABLE = [
        {'name': 'cluster-id', 'required': True,
         'help_text': 'Cluster Id of cluster you want to get file from'},
        {'name': 'key-pair-file', 'required': True,
         'help_text': 'Private key file to use for login'},
        {'name': 'src', 'required': True,
         'help_text': 'Source file path on remote host'},
        {'name': 'dest', 'help_text': 'Destination file path on your machine'},
        {'name': 'ssh-options', 'nargs': '+',
         'help_text': SSH_OPTIONS_HELP_TEXT},
    ]

    def _run_main_command(self, parsed_args, parsed_globals):
        master_dns = sshutils.validate_and_find_master_dns(
            session=self._session,
            parsed_globals=parsed_globals,
            cluster_id=parsed_args.cluster_id)

        key_file = parsed_args.key_pair_file
        sshutils.validate_scp_with_key_file(key_file)
        if (emrutils.which('scp') or emrutils.which('scp.exe')):
            ssh_options = _build_ssh_options(parsed_args.ssh_options)
            command = ['scp', '-r'] + ssh_options + [
                '-i', parsed_args.key_pair_file, constants.SSH_USER + '@' +
                master_dns + ':' + parsed_args.src]
        else:
            if parsed_args.ssh_options:
                sys.stderr.write(PUTTY_SSH_OPTIONS_MSG)
            command = ['pscp', '-scp', '-r', '-i', parsed_args.key_pair_file,
                       constants.SSH_USER + '@' + master_dns + ':' +
                       parsed_args.src]

        if parsed_args.dest:
            command.append(parsed_args.dest)
        else:
            command.append(parsed_args.src.split('/')[-1])
        print(' '.join(command))
        rc = subprocess.call(command)
        return rc
