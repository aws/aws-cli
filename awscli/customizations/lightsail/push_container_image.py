# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import errno
import json
import logging
import subprocess
import awscli
from awscli.compat import ignore_user_entered_signals
from awscli.customizations.commands import BasicCommand
from awscli.customizations.lightsail import helptext

logger = logging.getLogger(__name__)

ERROR_MESSAGE = (
    'The Lightsail Control (lightsailctl) plugin was not found. ',
    'To download and install it, see ',
    'https://lightsail.aws.amazon.com/ls/docs/en_us/articles/amazon-lightsail-install-software'
)

INPUT_VERSION = '1'

class PushContainerImage(BasicCommand):
    NAME = 'push-container-image'

    DESCRIPTION = 'Push container image for use in a service deployment.'

    ARG_TABLE = [
        {
            'name': 'service-name',
            'help_text': helptext.SERVICENAME,
            'required': True
        },
        {
            'name': 'image',
            'help_text': helptext.IMAGE,
            'required': True
        },
        {
            'name': 'label',
            'help_text': helptext.LABEL,
            'required': True
        }]

    def _run_main(self, parsed_args, parsed_globals):
        payload = self._get_input_request(parsed_args, parsed_globals)
        try:
            # ignore_user_entered_signals ignores these signals
            # because if signals which kills the process are not
            # captured would kill the foreground process but not the
            # background one. Capturing these would prevents process
            # from getting killed and these signals are input to plugin
            # and handling in there
            with ignore_user_entered_signals():
                # call executable with necessary input
                subprocess.run(
                    ['lightsailctl', '--plugin', '--input-stdin'],
                    input=json.dumps(payload).encode('utf-8'),
                    check=True)
            return 0
        except OSError as ex:
            if ex.errno == errno.ENOENT:
                logger.debug('lightsailctl not found',
                             exc_info=True)
                raise ValueError(''.join(ERROR_MESSAGE))

    def _get_input_request(self, parsed_args, parsed_globals):
        input_request = {
            'inputVersion' : INPUT_VERSION,
            'operation': 'PushContainerImage',
        }

        payload = dict(
            service=parsed_args.service_name,
            image=parsed_args.image,
            label=parsed_args.label
        )

        configuration = {}
        configuration['debug'] = parsed_globals.debug

        if parsed_globals.endpoint_url is not None:
            configuration['endpoint'] = parsed_globals.endpoint_url

        if parsed_globals.verify_ssl is not None:
            configuration['doNotVerifySSL'] = not parsed_globals.verify_ssl

        configuration['paginate'] = parsed_globals.paginate

        if parsed_globals.output is not None:
            configuration['output'] = parsed_globals.output

        if parsed_globals.query is not None:
            configuration['query'] = parsed_globals.query

        if parsed_globals.profile:
            configuration['profile'] = parsed_globals.profile
        elif self._session.get_config_variable('profile'):
            configuration['profile'] = \
                self._session.get_config_variable('profile')

        if parsed_globals.region:
            configuration['region'] = parsed_globals.region
        elif self._session.get_config_variable('region'):
            configuration['region'] = \
                self._session.get_config_variable('region')

        configuration['doNotSignRequest'] = not parsed_globals.sign_request

        if parsed_globals.ca_bundle:
            configuration['caBundle'] = parsed_globals.ca_bundle
        elif self._session.get_config_variable('ca_bundle'):
            configuration['caBundle'] = \
                self._session.get_config_variable('ca_bundle')

        if parsed_globals.read_timeout is not None:
            configuration['readTimeout'] = parsed_globals.read_timeout

        if parsed_globals.connect_timeout is not None:
            configuration['connectTimeout'] = parsed_globals.connect_timeout

        if parsed_globals.cli_binary_format is not None:
            configuration['cliBinaryFormat'] = parsed_globals.cli_binary_format

        configuration['cliVersion'] = awscli.__version__

        input_request['payload'] = payload
        input_request['configuration'] = configuration
        return input_request
