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
"""
This customization provides a simpler interface for the ``ses send-email``
command.  This simplified form is based on the legacy CLI.  The simple format
will be::

aws ses send-email --subject SUBJECT --from FROM_EMAIL
    --to-addresses addr ... --cc-addresses addr ...
    --bcc-addresses addr ... --reply-to-addresses addr ...
    --return-path addr --text TEXTBODY --html HTMLBODY

"""

from awscli.customizations import utils
from awscli.arguments import CustomArgument
from awscli.customizations.utils import validate_mutually_exclusive_handler


TO_HELP = ('The email addresses of the primary recipients.  '
           'You can specify multiple recipients as space-separated values')
CC_HELP = ('The email addresses of copy recipients (Cc).  '
           'You can specify multiple recipients as space-separated values')
BCC_HELP = ('The email addresses of blind-carbon-copy recipients (Bcc).  '
            'You can specify multiple recipients as space-separated values')
SUBJECT_HELP = 'The subject of the message'
TEXT_HELP = 'The raw text body of the message'
HTML_HELP = 'The HTML body of the message'


def register_ses_send_email(event_handler):
    event_handler.register('building-argument-table.ses.send-email',
                           _promote_args)
    event_handler.register(
        'operation-args-parsed.ses.send-email',
        validate_mutually_exclusive_handler(
            ['destination'], ['to', 'cc', 'bcc']))
    event_handler.register(
        'operation-args-parsed.ses.send-email',
        validate_mutually_exclusive_handler(
            ['message'], ['text', 'html']))


def _promote_args(argument_table, **kwargs):
    argument_table['message'].required = False
    argument_table['destination'].required = False
    utils.rename_argument(argument_table, 'source',
                          new_name='from')
    argument_table['to'] = AddressesArgument(
        'to', 'ToAddresses', help_text=TO_HELP)
    argument_table['cc'] = AddressesArgument(
        'cc', 'CcAddresses', help_text=CC_HELP)
    argument_table['bcc'] = AddressesArgument(
        'bcc', 'BccAddresses', help_text=BCC_HELP)
    argument_table['subject'] = BodyArgument(
        'subject', 'Subject', help_text=SUBJECT_HELP)
    argument_table['text'] = BodyArgument(
        'text', 'Text', help_text=TEXT_HELP)
    argument_table['html'] = BodyArgument(
        'html', 'Html', help_text=HTML_HELP)


def _build_destination(params, key, value):
    # Build up the Destination data structure
    if 'Destination' not in params:
        params['Destination'] = {}
    params['Destination'][key] = value


def _build_message(params, key, value):
    # Build up the Message data structure
    if 'Message' not in params:
        params['Message'] = {'Subject': {}, 'Body': {}}
    if key in ('Text', 'Html'):
        params['Message']['Body'][key] = {'Data': value}
    elif key == 'Subject':
        params['Message']['Subject'] = {'Data': value}


class AddressesArgument(CustomArgument):

    def __init__(self, name, json_key, help_text='', dest=None, default=None,
                 action=None, required=None, choices=None, cli_type_name=None):
        super(AddressesArgument, self).__init__(name=name, help_text=help_text,
                                                required=required, nargs='+')
        self._json_key = json_key

    def add_to_params(self, parameters, value):
        if value:
            _build_destination(parameters, self._json_key, value)


class BodyArgument(CustomArgument):

    def __init__(self, name, json_key, help_text='', required=None):
        super(BodyArgument, self).__init__(name=name, help_text=help_text,
                                           required=required)
        self._json_key = json_key

    def add_to_params(self, parameters, value):
        if value:
            _build_message(parameters, self._json_key, value)

