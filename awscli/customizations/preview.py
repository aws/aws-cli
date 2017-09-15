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


logger = logging.getLogger(__name__)


PREVIEW_SERVICES = [
    'sdb',
]


def register_preview_commands(events):
    events.register('building-command-table.main', mark_as_preview)


def mark_as_preview(command_table, session, **kwargs):
    # These are services that are marked as preview but are
    # explicitly enabled in the config file.
    allowed_services = _get_allowed_services(session)
    for preview_service in PREVIEW_SERVICES:
        is_enabled = False
        if preview_service in allowed_services:
            # Then we don't need to swap it as a preview
            # service, the user has specifically asked to
            # enable this service.
            logger.debug("Preview service enabled through config file: %s",
                         preview_service)
            is_enabled = True
        original_command = command_table[preview_service]
        preview_cls = type(
            'PreviewCommand',
            (PreviewModeCommandMixin, original_command.__class__), {})
        command_table[preview_service] = preview_cls(
            cli_name=original_command.name,
            session=session,
            service_name=original_command.service_model.service_name,
            is_enabled=is_enabled)
        # We also want to register a handler that will update the
        # description in the docs to say that this is a preview service.
        session.get_component('event_emitter').register_last(
            'doc-description.%s' % preview_service,
            update_description_with_preview)


def update_description_with_preview(help_command, **kwargs):
    style = help_command.doc.style
    style.start_note()
    style.bold(PreviewModeCommandMixin.HELP_SNIPPET.strip())
    # bcdoc does not currently allow for what I'd like to do
    # which is have a code block like:
    #
    # ::
    #    [preview]
    #    service=true
    #
    #    aws configure set preview.service true
    #
    # So for now we're just going to add the configure command
    # to enable this.
    style.doc.write("You can enable this service by running: ")
    # The service name will always be the first element in the
    # event class for the help object
    service_name = help_command.event_class.split('.')[0]
    style.code("aws configure set preview.%s true" % service_name)
    style.end_note()


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


class PreviewModeCommandMixin(object):
    ENABLE_DOCS = textwrap.dedent("""\
    However, if you'd like to use the "aws {service}" commands with the
    AWS CLI, you can enable this service by adding the following to your CLI
    config file:

        [preview]
        {service}=true

    or by running:

        aws configure set preview.{service} true

    """)
    HELP_SNIPPET = ("AWS CLI support for this service is only "
                    "available in a preview stage.\n")

    def __init__(self, *args, **kwargs):
        self._is_enabled = kwargs.pop('is_enabled')
        super(PreviewModeCommandMixin, self).__init__(*args, **kwargs)

    def __call__(self, args, parsed_globals):
        if self._is_enabled or self._is_help_command(args):
            return super(PreviewModeCommandMixin, self).__call__(
                args, parsed_globals)
        else:
            return self._display_opt_in_message()

    def _is_help_command(self, args):
        return args and args[-1] == 'help'

    def _display_opt_in_message(self):
        sys.stderr.write(self.HELP_SNIPPET)
        sys.stderr.write("\n")
        # Then let them know how to enable this service.
        sys.stderr.write(self.ENABLE_DOCS.format(service=self._service_name))
        return 1
