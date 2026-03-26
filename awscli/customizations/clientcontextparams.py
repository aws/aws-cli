# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from functools import partial

from awscli.arguments import BaseCLIArgument
from awscli.botocore import xform_name
from awscli.botocore.config import Config

logger = logging.getLogger(__name__)

_SUPPORTED_TYPES = ('boolean', 'string')


def register_client_context_params(event_handlers):
    event_handlers.register(
        'building-argument-table', inject_client_context_params
    )


def inject_client_context_params(
    argument_table, operation_model, event_name, session, **kwargs
):
    service_model = operation_model.service_model
    if not hasattr(service_model, 'client_context_parameters'):
        return
    context_params = service_model.client_context_parameters
    if not context_params:
        return

    parsed_args_event = event_name.replace(
        'building-argument-table.', 'operation-args-parsed.'
    )
    param_defs = []
    for param in context_params:
        cli_name = xform_name(param.name, '-')
        # Skip if an operation input member has the same CLI name;
        # the model validation test will catch this before release.
        if cli_name in argument_table:
            logger.debug(
                'Skipping client context param %s for %s: '
                'collision with existing argument',
                param.name,
                service_model.service_name,
            )
            continue
        # Skip types we don't handle yet; the model validation test
        # will catch new types before they reach customers.
        if param.type not in _SUPPORTED_TYPES:
            logger.debug(
                'Skipping client context param %s for %s: '
                'unsupported type %r',
                param.name,
                service_model.service_name,
                param.type,
            )
            continue
        arg = ClientContextParamArgument(
            name=cli_name,
            context_param_name=param.name,
            param_type=param.type,
            documentation=getattr(param, 'documentation', ''),
            group_name=cli_name if param.type == 'boolean' else None,
        )
        argument_table[cli_name] = arg
        if param.type == 'boolean':
            negative = ClientContextParamArgument(
                name='no-' + cli_name,
                context_param_name=param.name,
                param_type=param.type,
                action='store_false',
                dest=cli_name.replace('-', '_'),
                group_name=cli_name,
            )
            argument_table['no-' + cli_name] = negative
        param_defs.append((cli_name, param.name))

    if param_defs:
        session.register(
            parsed_args_event,
            partial(_apply_client_context_params, param_defs, session),
        )


def _apply_client_context_params(param_defs, session, parsed_args, **kwargs):
    context_params = {}
    for cli_name, original_name in param_defs:
        py_name = cli_name.replace('-', '_')
        value = getattr(parsed_args, py_name, None)
        if value is not None:
            context_params[original_name] = value
    if not context_params:
        return
    new_config = Config(client_context_params=context_params)
    existing = session.get_default_client_config()
    if existing is not None:
        new_config = existing.merge(new_config)
    session.set_default_client_config(new_config)


class ClientContextParamArgument(BaseCLIArgument):
    def __init__(
        self,
        name,
        context_param_name,
        param_type,
        documentation='',
        action='store_true',
        dest=None,
        group_name=None,
    ):
        self.argument_model = None
        self._name = name
        self._context_param_name = context_param_name
        self._param_type = param_type
        self._documentation = documentation
        self._required = False
        self._action = action
        self._dest = dest or name.replace('-', '_')
        self._group_name = group_name

    @property
    def cli_name(self):
        return '--' + self._name

    @property
    def cli_type_name(self):
        return self._param_type

    @property
    def required(self):
        return self._required

    @required.setter
    def required(self, value):
        self._required = value

    @property
    def documentation(self):
        return self._documentation

    @property
    def group_name(self):
        return self._group_name

    def add_to_parser(self, parser):
        if self._param_type == 'boolean':
            parser.add_argument(
                self.cli_name,
                dest=self._dest,
                action=self._action,
                default=None,
            )
        else:
            parser.add_argument(
                self.cli_name,
                dest=self._dest,
            )

    def add_to_params(self, parameters, value):
        # Client context params are not operation parameters;
        # they are applied via _apply_client_context_params.
        pass
