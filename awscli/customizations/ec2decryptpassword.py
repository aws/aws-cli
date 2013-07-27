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
import logging
import os
import base64
import rsa
import six

from awscli.clidriver import BaseCLIArgument
from botocore.parameters import StringParameter

logger = logging.getLogger(__name__)


HELP = """<p>The file that contains the private key used to launch
the instance (e.g. windows-keypair.pem).  If this is supplied, the
password data sent from EC2 will be decrypted before display.</p>"""


# This is a bit kludgy.
# We need a way to pass some state between the event handlers.
# One event handler determines if a path to the private key
# file was specified and, if so, validates the path.
# The other event handler attempts to decrypt the password data
# if a private key path was specified.
# I'm using the module-level globalvar to maintain that shared
# state.  In the context of a CLI, I think that's okay.

_key_path = None

def _set_key_path(path):
    global _key_path
    _key_path = path

def _get_key_path():
    global _key_path
    return _key_path


def decrypt_password_data(event_name, shape, value, **kwargs):
    """
    This handler gets called after the PasswordData element of the
    response has been parsed.  It checks to see if a private launch
    key was specified on the command.  If it was, it tries to use
    that private key to decrypt the password data and return it.
    """
    key_path = _get_key_path()
    if key_path:
        logger.debug('decrypt_password_data: %s', key_path)
        try:
            private_key_file = open(key_path)
            private_key_contents = private_key_file.read()
            private_key_file.close()
            private_key = rsa.PrivateKey.load_pkcs1(six.b(private_key_contents))
            value = base64.b64decode(value)
            value = rsa.decrypt(value, private_key)
        except:
            # TODO
            # Should we raise an exception or just return the
            # unencrypted data?  Or maybe just print a message?
            logger.debug('Unable to decrypt PasswordData', exc_info=True)
            msg = ('Unable to decrypt password data using '
                   'provided private key file.')
            raise ValueError(msg)
    return value


def ec2_add_priv_launch_key(argument_table, operation, **kwargs):
    """
    This handler gets called after the argument table for the
    operation has been created.  It's job is to add the
    ``priv-launch-key`` parameter.
    """
    argument_table['priv-launch-key'] = LaunchKeyArgument(operation,
                                                          'priv-launch-key')

    
def ec2_process_priv_launch_key(operation, parsed_args, **kwargs):
    """
    This handler gets called after the command line arguments to
    the ``get-password-data`` command have been parsed.  It is
    passed the ``Operation`` object and the ``Namespace`` containing
    the parsed args.

    It needs to check to see if ``priv-launch-key`` was supplied
    by the user.  If it was, it checks to make sure the path provided
    points to a real file and, if so, stores the path in the module
    global var for access later by the decrypt method.
    """
    if parsed_args.priv_launch_key:
        path = os.path.expandvars(parsed_args.priv_launch_key)
        path = os.path.expanduser(path)
        logger.debug(path)
        if os.path.isfile(path):
            _set_key_path(path)
        else:
            msg = ('priv-launch-key should be a path to the '
                   'local SSH private key file used to launch '
                   'the instance.')
            raise ValueError(msg)


class LaunchKeyArgument(BaseCLIArgument):

    def __init__(self, operation, name):
        param = StringParameter(operation,
                                name='priv_launch_key',
                                type='string')
        super(LaunchKeyArgument, self).__init__(
            name, argument_object=param)
        self._operation = operation
        self._name = name

    @property
    def cli_name(self):
        return '--' + self._name

    @property
    def cli_type_name(self):
        return 'string'

    @property
    def required(self):
        return False

    @property
    def documentation(self):
        return HELP

    def add_to_parser(self, parser, cli_name=None):
        parser.add_argument(self.cli_name, metavar=self.py_name,
                            help='Number of instances to launch')

    def add_to_params(self, parameters, value):
        """
        Since the extra ``priv-launch-key`` parameter is local and
        doesn't need to be sent to the service, we don't have to do
        anything here.
        """
        pass
