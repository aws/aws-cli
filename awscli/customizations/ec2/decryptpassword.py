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

from botocore import model

from awscli.arguments import BaseCLIArgument


logger = logging.getLogger(__name__)


HELP = """<p>The file that contains the private key used to launch
the instance (e.g. windows-keypair.pem).  If this is supplied, the
password data sent from EC2 will be decrypted before display.</p>"""


def ec2_add_priv_launch_key(argument_table, operation_model, session,
                            **kwargs):
    """
    This handler gets called after the argument table for the
    operation has been created.  It's job is to add the
    ``priv-launch-key`` parameter.
    """
    argument_table['priv-launch-key'] = LaunchKeyArgument(
        session, operation_model, 'priv-launch-key')


class LaunchKeyArgument(BaseCLIArgument):

    def __init__(self, session, operation_model, name):
        self._session = session
        self.argument_model = model.Shape('LaunchKeyArgument', {'type': 'string'})
        self._operation_model = operation_model
        self._name = name
        self._key_path = None
        self._required = False

    @property
    def cli_type_name(self):
        return 'string'

    @property
    def required(self):
        return self._required

    @required.setter
    def required(self, value):
        self._required = value

    @property
    def documentation(self):
        return HELP

    def add_to_parser(self, parser):
        parser.add_argument(self.cli_name, dest=self.py_name,
                            help='SSH Private Key file')

    def add_to_params(self, parameters, value):
        """
        This gets called with the value of our ``--priv-launch-key``
        if it is specified.  It needs to determine if the path
        provided is valid and, if it is, it stores it in the instance
        variable ``_key_path`` for use by the decrypt routine.
        """
        if value:
            path = os.path.expandvars(value)
            path = os.path.expanduser(path)
            if os.path.isfile(path):
                self._key_path = path
                endpoint_prefix = \
                    self._operation_model.service_model.endpoint_prefix
                event = 'after-call.%s.%s' % (endpoint_prefix,
                                              self._operation_model.name)
                self._session.register(event, self._decrypt_password_data)
            else:
                msg = ('priv-launch-key should be a path to the '
                       'local SSH private key file used to launch '
                       'the instance.')
                raise ValueError(msg)

    def _decrypt_password_data(self, parsed, **kwargs):
        """
        This handler gets called after the GetPasswordData command has been
        executed.  It is called with the and the ``parsed`` data.  It checks to
        see if a private launch key was specified on the command.  If it was,
        it tries to use that private key to decrypt the password data and
        replace it in the returned data dictionary.
        """
        if self._key_path is not None:
            logger.debug("Decrypting password data using: %s", self._key_path)
            value = parsed.get('PasswordData')
            if not value:
                return
            try:
                with open(self._key_path) as pk_file:
                    pk_contents = pk_file.read()
                    private_key = rsa.PrivateKey.load_pkcs1(pk_contents.encode("latin-1"))
                    value = base64.b64decode(value)
                    value = rsa.decrypt(value, private_key)
                    logger.debug(parsed)
                    parsed['PasswordData'] = value.decode('utf-8')
                    logger.debug(parsed)
            except Exception:
                logger.debug('Unable to decrypt PasswordData', exc_info=True)
                msg = ('Unable to decrypt password data using '
                       'provided private key file.')
                raise ValueError(msg)
