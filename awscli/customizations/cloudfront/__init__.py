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
from awscli.customizations.cloudfront.arguments import (
    CreateDefaultRootObject,
    OriginDomainName,
    UpdateDefaultRootObject,
    add_paths_argument,
)
from awscli.customizations.cloudfront.sign import (
    SignCommand,
    SignCookiesCommand,
)
from awscli.customizations.utils import validate_mutually_exclusive_handler


def register(event_handler):
    event_handler.register(
        'building-command-table.cloudfront', inject_commands
    )

    # Provides a simpler --paths for ``aws cloudfront create-invalidation``
    event_handler.register(
        'building-argument-table.cloudfront.create-invalidation',
        add_paths_argument,
    )
    event_handler.register(
        'operation-args-parsed.cloudfront.create-invalidation',
        validate_mutually_exclusive_handler(['invalidation_batch'], ['paths']),
    )

    event_handler.register(
        'operation-args-parsed.cloudfront.create-distribution',
        validate_mutually_exclusive_handler(
            ['default_root_object', 'origin_domain_name'],
            ['distribution_config'],
        ),
    )
    event_handler.register(
        'building-argument-table.cloudfront.create-distribution',
        lambda argument_table, **kwargs: argument_table.__setitem__(
            'origin-domain-name', OriginDomainName(argument_table)
        ),
    )
    event_handler.register(
        'building-argument-table.cloudfront.create-distribution',
        lambda argument_table, **kwargs: argument_table.__setitem__(
            'default-root-object', CreateDefaultRootObject(argument_table)
        ),
    )

    context = {}
    event_handler.register(
        'top-level-args-parsed', context.update, unique_id='cloudfront'
    )
    event_handler.register(
        'operation-args-parsed.cloudfront.update-distribution',
        validate_mutually_exclusive_handler(
            ['default_root_object'], ['distribution_config']
        ),
    )
    event_handler.register(
        'building-argument-table.cloudfront.update-distribution',
        lambda argument_table, **kwargs: argument_table.__setitem__(
            'default-root-object',
            UpdateDefaultRootObject(
                context=context, argument_table=argument_table
            ),
        ),
    )


def inject_commands(command_table, session, **kwargs):
    command_table['sign'] = SignCommand(session)
    command_table['sign-cookies'] = SignCookiesCommand(session)
