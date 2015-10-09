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
from botocore.utils import parse_to_aware_datetime
from awscli.customizations.commands import BasicCommand
from .cfsign import sign
from .cfutils import datetime2epoch


def initialize(cli):
    """
    The entry point for high level commands.
    """
    cli.register('building-command-table.cloudfront', inject_commands)


def inject_commands(command_table, session, **kwargs):
    """
    Called when the command table is being built. Used to inject new
    high level commands into the command list. These high level commands
    must not collide with existing low-level API call names.
    """
    command_table['sign'] = CloudFrontSign(session)


class CloudFrontSign(BasicCommand):
    NAME = 'sign'
    DESCRIPTION = 'Sign a given url.'
    DATETIME_HELP_TEXT = """Acceptable formats include:
        YYYY-MM-DD, YYYY-MM-DDThh:mm:ssZ,
        YYYY-MM-DDThh:mm:ss+hh:mm (with offset), or EpochTime.
        Do NOT use YYYYMMDD, because it will be treated as EpochTime."""
    ARG_TABLE = [
        {
            'name': 'url',
            'no_paramfile': True,  # To disable the default paramfile behavior
            'required': True,
            'help_text': 'The URL to be signed',
        },
        {
            'name': 'key-pair-id',
            'required': True,
            'help_text': 'The ID of your CloudFront key pairs.',
        },
        {
            'name': 'private-key',
            'required': True,
            'help_text': 'file://path/to/your/private-key.pem',
        },
        {'name': 'expires', 'required': True, 'help_text': DATETIME_HELP_TEXT},
        {'name': 'starts', 'help_text': DATETIME_HELP_TEXT},
        {'name': 'ip-address', 'help_text': 'Format: x.x.x.x/x or x.x.x.x'},
    ]

    def _run_main(self, args, parsed_globals):
        print(sign(
            args.url,
            args.key_pair_id,
            args.private_key,
            datetime2epoch(parse_to_aware_datetime(args.expires)),
            datetime2epoch(parse_to_aware_datetime(args.starts))
                if args.starts else None,
            args.ip_address,
            ))
        return 0
