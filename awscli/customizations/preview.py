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
"""This module enables the preview-mode customization.

If a service is marked as being in preview mode, then any attempts
to call operations on that service will print a message pointing
the user to alternate solutions.  A user can still access this
service by enabling the service in their config file via:

    [preview]
    servicename=true

or by running:

    aws configure set preview.servicename true

Also any service that is marked as being in preview will *not*
be listed in the help docs, unless the service has been enabled
in the config file as shown above.

"""
import logging
import sys
import textwrap

from awscli.clidriver import CLICommand


logger = logging.getLogger(__name__)

# Mapping of service name to help text to print
# when a user tries to invoke a service marked as preview.
CLOUDSEARCH_HELP = """
CloudSearch has a specialized command line tool available at
http://aws.amazon.com/tools#cli. The AWS CLI does not yet
support all of the features of the CloudSearch CLI. Until these features
are added to the AWS CLI, you may have a more complete
experience using the CloudSearch CLI.
"""


GENERAL_HELP = """
This service is only available as a preview service.
"""


PREVIEW_SERVICES = {
    'cloudfront': GENERAL_HELP,
    'sdb': GENERAL_HELP,
}


def register_preview_commands(events):
    events.register('building-command-table.main', mark_as_preview)


def mark_as_preview(command_table, session, **kwargs):
    # These are services that are marked as preview but are
    # explicitly enabled in the config file.
    allowed_services = _get_allowed_services(session)
    for preview_service in PREVIEW_SERVICES:
        if preview_service in allowed_services:
            # Then we don't need to swap it as a preview
            # service, the user has specifically asked to
            # enable this service.
            logger.debug("Preview service enabled through config file: %s",
                         preview_service)
            continue
        command_table[preview_service] = PreviewModeCommand(
            preview_service, PREVIEW_SERVICES[preview_service])


def _get_allowed_services(session):
    # For a service to be marked as preview, it must be in the
    # [preview] section and it must have a value of 'true'
    # (case insensitive).
    allowed = []
    preview_services = session.full_config.get('preview', {})
    for preview, value in preview_services.items():
        if value == 'true':
            allowed.append(preview)
    return allowed


class PreviewModeCommand(CLICommand):
    # This is a hidden attribute that tells the doc system
    # not to document this command in the provider help.
    # This is an internal implementation detail.
    _UNDOCUMENTED = True

    ENABLE_DOCS = textwrap.dedent("""\
    However, if you'd like to use a basic set of {service} commands with the
    AWS CLI, you can enable this service by adding the following to your CLI
    config file:

        [preview]
        {service}=true

    or by running:

        aws configure set preview.{service} true

    """)

    def __init__(self, service_name, service_help):
        self._service_name = service_name
        self._service_help = service_help

    def __call__(self, args, parsed_globals):
        sys.stderr.write(self._service_help)
        sys.stderr.write("\n")
        # Then let them know how to enable this service.
        sys.stderr.write(self.ENABLE_DOCS.format(service=self._service_name))
        return 1
