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
"""This module has customizations to unify paging paramters.

For any operation that can be paginated, we will:

    * Hide the service specific pagination params.  This can vary across
    services and we're going to replace them with a consistent set of
    arguments.  The arguments will still work, but they are not
    documented.  This allows us to add a pagination config after
    the fact and still remain backwards compatible with users that
    were manually doing pagination.
    * Add a ``--starting-token`` and a ``--max-items`` argument.

"""
import logging
from functools import partial

from botocore import xform_name
from botocore.exceptions import DataNotFoundError, PaginationError
from botocore import model

from awscli.arguments import BaseCLIArgument


logger = logging.getLogger(__name__)


STARTING_TOKEN_HELP = """
<p>A token to specify where to start paginating.  This is the
<code>NextToken</code> from a previously truncated response.</p>
"""

MAX_ITEMS_HELP = """
<p>The total number of items to return.  If the total number
of items available is more than the value specified in
max-items then a <code>NextToken</code> will
be provided in the output that you can use to resume pagination.
This <code>NextToken</code> response element should <b>not</b> be
used directly outside of the AWS CLI.</p>
"""

PAGE_SIZE_HELP = """
<p>The size of each page.<p>
"""


def register_pagination(event_handlers):
    event_handlers.register('building-argument-table', unify_paging_params)
    event_handlers.register_last('doc-description', add_paging_description)


def get_paginator_config(session, service_name, operation_name):
    try:
        paginator_model = session.get_paginator_model(service_name)
    except DataNotFoundError:
        return None
    try:
        operation_paginator_config = paginator_model.get_paginator(
            operation_name)
    except ValueError:
        return None
    return operation_paginator_config


def add_paging_description(help_command, **kwargs):
    # This customization is only applied to the description of
    # Operations, so we must filter out all other events.
    if not isinstance(help_command.obj, model.OperationModel):
        return
    service_name = help_command.obj.service_model.service_name
    paginator_config = get_paginator_config(
        help_command.session, service_name, help_command.obj.name)
    if not paginator_config:
        return
    help_command.doc.style.new_paragraph()
    help_command.doc.writeln(
        ('``%s`` is a paginated operation. Multiple API calls may be issued '
         'in order to retrieve the entire data set of results. You can '
         'disable pagination by providing the ``--no-paginate`` argument.')
        % help_command.name)
    # Only include result key information if it is present.
    if paginator_config.get('result_key'):
        queries = paginator_config['result_key']
        if type(queries) is not list:
            queries = [queries]
        queries = ", ".join([('``%s``' % s) for s in queries])
        help_command.doc.writeln(
            ('When using ``--output text`` and the ``--query`` argument on a '
             'paginated response, the ``--query`` argument must extract data '
             'from the results of the following query expressions: %s')
            % queries)


def unify_paging_params(argument_table, operation_model, event_name,
                        session, **kwargs):
    paginator_config = get_paginator_config(
        session, operation_model.service_model.service_name,
        operation_model.name)
    if paginator_config is None:
        # We only apply these customizations to paginated responses.
        return
    logger.debug("Modifying paging parameters for operation: %s",
                 operation_model.name)
    _remove_existing_paging_arguments(argument_table, paginator_config)
    parsed_args_event = event_name.replace('building-argument-table.',
                                           'operation-args-parsed.')
    shadowed_args = {}
    add_paging_argument(argument_table, 'starting-token',
                        PageArgument('starting-token', STARTING_TOKEN_HELP,
                                     parse_type='string',
                                     serialized_name='StartingToken'),
                        shadowed_args)
    input_members = operation_model.input_shape.members
    type_name = 'integer'
    if 'limit_key' in paginator_config:
        limit_key_shape = input_members[paginator_config['limit_key']]
        type_name = limit_key_shape.type_name
        if type_name not in PageArgument.type_map:
            raise TypeError(
                ('Unsupported pagination type {0} for operation {1}'
                 ' and parameter {2}').format(
                    type_name, operation_model.name,
                    paginator_config['limit_key']))
        add_paging_argument(argument_table, 'page-size',
                            PageArgument('page-size', PAGE_SIZE_HELP,
                                         parse_type=type_name,
                                         serialized_name='PageSize'),
                            shadowed_args)

    add_paging_argument(argument_table, 'max-items',
                        PageArgument('max-items', MAX_ITEMS_HELP,
                                     parse_type=type_name,
                                     serialized_name='MaxItems'),
                        shadowed_args)
    session.register(
        parsed_args_event,
        partial(check_should_enable_pagination,
                list(_get_all_cli_input_tokens(paginator_config)),
                shadowed_args, argument_table))


def add_paging_argument(argument_table, arg_name, argument, shadowed_args):
    if arg_name in argument_table:
        # If there's already an entry in the arg table for this argument,
        # this means we're shadowing an argument for this operation.  We
        # need to store this later in case pagination is turned off because
        # we put these arguments back.
        # See the comment in check_should_enable_pagination() for more info.
        shadowed_args[arg_name] = argument_table[arg_name]
    argument_table[arg_name] = argument


def check_should_enable_pagination(input_tokens, shadowed_args, argument_table,
                                   parsed_args, parsed_globals, **kwargs):
    normalized_paging_args = ['start_token', 'max_items']
    for token in input_tokens:
        py_name = token.replace('-', '_')
        if getattr(parsed_args, py_name) is not None and \
                py_name not in normalized_paging_args:
            # The user has specified a manual (undocumented) pagination arg.
            # We need to automatically turn pagination off.
            logger.debug("User has specified a manual pagination arg. "
                         "Automatically setting --no-paginate.")
            parsed_globals.paginate = False

            # Because pagination is now disabled, there's a chance that
            # we were shadowing arguments.  For example, we inject a
            # --max-items argument in unify_paging_params().  If the
            # the operation also provides its own MaxItems (which we
            # expose as --max-items) then our custom pagination arg
            # was shadowing the customers arg.  When we turn pagination
            # off we need to put back the original argument which is
            # what we're doing here.
            for key, value in shadowed_args.items():
                argument_table[key] = value
    
    if not parsed_globals.paginate:
        ensure_paging_params_not_set(parsed_args, shadowed_args)


def ensure_paging_params_not_set(parsed_args, shadowed_args):
    paging_params = ['starting_token', 'page_size', 'max_items']
    shadowed_params = [p.replace('-', '_') for p in shadowed_args.keys()]
    params_used = [p for p in paging_params if
                   p not in shadowed_params and getattr(parsed_args, p)]

    if len(params_used) > 0:
        converted_params = ', '.join(
            ["--" + p.replace('_', '-') for p in params_used])
        raise PaginationError(
            message="Cannot specify --no-paginate along with pagination "
                    "arguments: %s" % converted_params)


def _remove_existing_paging_arguments(argument_table, pagination_config):
    for cli_name in _get_all_cli_input_tokens(pagination_config):
        argument_table[cli_name]._UNDOCUMENTED = True


def _get_all_cli_input_tokens(pagination_config):
    # Get all input tokens including the limit_key
    # if it exists.
    tokens = _get_input_tokens(pagination_config)
    for token_name in tokens:
        cli_name = xform_name(token_name, '-')
        yield cli_name
    if 'limit_key' in pagination_config:
        key_name = pagination_config['limit_key']
        cli_name = xform_name(key_name, '-')
        yield cli_name


def _get_input_tokens(pagination_config):
    tokens = pagination_config['input_token']
    if not isinstance(tokens, list):
        return [tokens]
    return tokens


def _get_cli_name(param_objects, token_name):
    for param in param_objects:
        if param.name == token_name:
            return param.cli_name.lstrip('-')


class PageArgument(BaseCLIArgument):
    type_map = {
        'string': str,
        'integer': int,
    }

    def __init__(self, name, documentation, parse_type, serialized_name):
        self.argument_model = model.Shape('PageArgument', {'type': 'string'})
        self._name = name
        self._serialized_name = serialized_name
        self._documentation = documentation
        self._parse_type = parse_type
        self._required = False

    @property
    def cli_name(self):
        return '--' + self._name

    @property
    def cli_type_name(self):
        return self._parse_type

    @property
    def required(self):
        return self._required

    @required.setter
    def required(self, value):
        self._required = value

    @property
    def documentation(self):
        return self._documentation

    def add_to_parser(self, parser):
        parser.add_argument(self.cli_name, dest=self.py_name,
                            type=self.type_map[self._parse_type])

    def add_to_params(self, parameters, value):
        if value is not None:
            pagination_config = parameters.get('PaginationConfig', {})
            pagination_config[self._serialized_name] = value
            parameters['PaginationConfig'] = pagination_config
