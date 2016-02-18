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

from awscli.customizations.emr import exceptions
from awscli.customizations.emr import emrutils
from awscli.customizations.emr import constants
from botocore.exceptions import WaiterError

LOG = logging.getLogger(__name__)


def validate_and_find_master_dns(session, parsed_globals, cluster_id):
    """
    Utility method for ssh, socks, put and get command.
    Check if the cluster to be connected to is
     terminated or being terminated.
    Check if the cluster is running.
    Find master instance public dns of a given cluster.
    Return the latest created master instance public dns name.
    Throw MasterDNSNotAvailableError or ClusterTerminatedError.
    """
    cluster_state = emrutils.get_cluster_state(
        session, parsed_globals, cluster_id)

    if cluster_state in constants.TERMINATED_STATES:
        raise exceptions.ClusterTerminatedError

    emr = emrutils.get_client(session, parsed_globals)

    try:
        cluster_running_waiter = emr.get_waiter('cluster_running')
        if cluster_state in constants.STARTING_STATES:
            print("Waiting for the cluster to start.")
        cluster_running_waiter.wait(ClusterId=cluster_id)
    except WaiterError:
        raise exceptions.MasterDNSNotAvailableError

    return emrutils.find_master_dns(
        session=session, cluster_id=cluster_id,
        parsed_globals=parsed_globals)


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
    if (emrutils.which('pscp.exe') is not None and
            (emrutils.which('scp.exe') or emrutils.which('scp')) is None):
        if check_command_key_format(key_file, ['ppk']) is False:
            raise exceptions.WrongPuttyKeyError
    else:
        pass


def check_ssh_key_format(key_file):
    # If only putty is present and the file format is incorrect
    if (emrutils.which('putty.exe') is not None and
            (emrutils.which('ssh.exe') or emrutils.which('ssh')) is None):
        if check_command_key_format(key_file, ['ppk']) is False:
            raise exceptions.WrongPuttyKeyError
    else:
        pass


def check_command_key_format(key_file, accepted_file_format=[]):
    if any(key_file.endswith(i) for i in accepted_file_format):
        return True
    else:
        return False
