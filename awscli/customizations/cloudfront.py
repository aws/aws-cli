# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import time
import random

import rsa
from botocore.utils import parse_to_aware_datetime
from botocore.signers import CloudFrontSigner

from awscli.arguments import CustomArgument
from awscli.customizations.utils import validate_mutually_exclusive_handler
from awscli.customizations.commands import BasicCommand


def register(event_handler):
    event_handler.register('building-command-table.cloudfront', _add_sign)

    # Provides a simpler --paths for ``aws cloudfront create-invalidation``
    event_handler.register(
        'building-argument-table.cloudfront.create-invalidation', _add_paths)
    event_handler.register(
        'operation-args-parsed.cloudfront.create-invalidation',
        validate_mutually_exclusive_handler(['invalidation_batch'], ['paths']))


def _add_paths(argument_table, **kwargs):
    argument_table['invalidation-batch'].required = False
    argument_table['paths'] = PathsArgument()


class PathsArgument(CustomArgument):

    def __init__(self):
        doc = (
            'The space-separated paths to be invalidated.'
            ' Note: --invalidation-batch and --paths are mututally exclusive.'
        )
        super(PathsArgument, self).__init__('paths', nargs='+', help_text=doc)

    def add_to_params(self, parameters, value):
        if value is not None:
            caller_reference = 'cli-%s-%s' % (
                int(time.time()), random.randint(1, 1000000))
            parameters['InvalidationBatch'] = {
                "CallerReference": caller_reference,
                "Paths": {"Quantity": len(value), "Items": value},
                }


def _add_sign(command_table, session, **kwargs):
    command_table['sign'] = SignCommand(session)


class SignCommand(BasicCommand):
    NAME = 'sign'
    DESCRIPTION = 'Sign a given url.'
    DATE_HELP = """Supported formats include:
        YYYY-MM-DD (which means 0AM UTC of that day),
        YYYY-MM-DDThh:mm:ss (with default timezone as UTC),
        YYYY-MM-DDThh:mm:ss+hh:mm or YYYY-MM-DDThh:mm:ss-hh:mm (with offset),
        or EpochTime.
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
        {'name': 'date-less-than', 'required': True, 'help_text': DATE_HELP},
        {'name': 'date-greater-than', 'help_text': DATE_HELP},
        {'name': 'ip-address', 'help_text': 'Format: x.x.x.x/x or x.x.x.x'},
    ]

    def _run_main(self, args, parsed_globals):
        signer = CloudFrontSigner(
            args.key_pair_id, RsaSigner(args.private_key).sign)
        date_less_than = parse_to_aware_datetime(args.date_less_than)
        if args.date_greater_than is not None:
            date_greater_than = parse_to_aware_datetime(args.date_greater_than)
        else:
            date_greater_than = None
        if date_greater_than is not None or args.ip_address is not None:
            policy = signer.build_policy(
                args.url, date_less_than, date_greater_than=date_greater_than,
                ip_address=args.ip_address)
            print(signer.generate_presigned_url(args.url, policy=policy))
        else:
            print(signer.generate_presigned_url(args.url, date_less_than))
        return 0


class RsaSigner(object):
    def __init__(self, private_key):
        self.priv_key = rsa.PrivateKey.load_pkcs1(private_key.encode('utf8'))

    def sign(self, message):
        return rsa.sign(message, self.priv_key, 'SHA-1')
