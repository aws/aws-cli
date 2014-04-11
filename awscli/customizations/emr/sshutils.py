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

import logging
import exceptions
import emrutils

LOG = logging.getLogger(__name__)


def validate_ssh_with_key_file(key_file):
    if (emrutils.which('putty.exe') or emrutils.which('ssh') or
            emrutils.which('ssh.exe')) is None:
        raise exceptions.SSHNotFoundError
    else:
        check_ssh_key_format(key_file)


def validate_scp_with_key_file(key_file):
    if (emrutils.which('pscp.exe') or emrutils.which('scp') or
            emrutils.which('scp.exe')) is None:
        raise exceptions.SCPNotFoundError
    else:
        check_scp_key_format(key_file)


def check_scp_key_format(key_file):
    # If only pscp is present and the file format is incorrect
    if (not check_command_key_format(key_file, ['ppk']) and
            emrutils.which('pscp.exe') and
            not (emrutils.which('scp') or emrutils.which('scp.exe'))):
        raise exceptions.WrongPuttyKeyError
    # Not checking for scp, as it has to be present if pscp is not
    elif (not check_command_key_format(key_file, ['cer', 'pem'])):
        raise exceptions.WrongSSHKeyError
    else:
        pass


def check_ssh_key_format(key_file):
    # If only putty is present and the file format is incorrect
    if (not check_command_key_format(key_file, ['ppk']) and
            emrutils.which('putty.exe') and
            not (emrutils.which('ssh.exe') or emrutils.which('ssh'))):
        raise exceptions.WrongPuttyKeyError
    # Not checking for ssh, as it has to be present if putty is not
    elif (not check_command_key_format(key_file, ['cer', 'pem'])):
        raise exceptions.WrongSSHKeyError
    else:
        pass


def check_command_key_format(key_file, accepted_file_format=[]):
    if any(key_file.endswith(i) for i in accepted_file_format):
        return True
    else:
        return False
