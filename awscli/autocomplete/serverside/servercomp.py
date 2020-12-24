# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.autocomplete.completer import BaseCompleter, CompletionResult
from awscli.autocomplete import LazyClientCreator
from awscli.autocomplete.filters import startswith_filter

LOG = logging.getLogger(__name__)


class ServerSideCompleter(BaseCompleter):
    def __init__(self, completion_lookup, client_creator,
                 response_filter=None):
        self._completion_lookup = completion_lookup
        self._client_creator = client_creator
        self._jmespath = None
        self._filter = response_filter
        if self._filter is None:
            self._filter = startswith_filter

    @property
    def jmespath(self):
        if self._jmespath is None:
            import jmespath
            self._jmespath = jmespath
        return self._jmespath

    def complete(self, parsed):
        """

        :param parsed: The parsed CLI command the user has typed.
        :type parsed:  awscli.autocomplete.parser.ParsedResult
        :return: A list of completion results, or None.
        :rtype: List[awscli.autocomplete.completer.CompletionResult]

        """
        if parsed.unparsed_items or parsed.current_fragment is None:
            return
        # This completer only applies to option values.  If the current fragment
        # we're on isn't an option value we can short circuit and return.
        if not self._on_cli_option_value_fragment(parsed):
            return
        completion_data = self._completion_lookup.get_server_completion_data(
            parsed.lineage, parsed.current_command, parsed.current_param,
        )
        if completion_data is None:
            return
        # At this point we know that this completer matches and we have
        # the information we need to actually generate completion suggestions.
        # We also know that we're only generate completoins that have a single
        # list element.  We'll need to update this once we support completions
        # with a 'parameters' key.
        raw_results = self._retrieve_remote_completion_data(
            parsed, completion_data['completions'][0])
        return self._filter(
            parsed.current_fragment,
            self._convert_to_completion_data(raw_results, parsed)
        )

    def _convert_to_completion_data(self, raw_results, parsed):
        index = -len(parsed.current_fragment)
        return [CompletionResult(r, index) for r in raw_results]

    def _on_cli_option_value_fragment(self, parsed):
        if parsed.current_param is None or parsed.current_fragment is None:
            return False
        return True

    def _get_client(self, service_name, parsed):
        return self._client_creator.create_client(
            service_name,
            parsed_region=parsed.global_params.get('region'),
            parsed_profile=parsed.global_params.get('profile')
        )

    def _retrieve_remote_completion_data(self, parsed, completion_data):
        # TODO: Handle global params that can affect how we create the client
        # (region, endpoint-url, profile, timeouts, etc).
        service_name = completion_data['service']
        client = self._get_client(service_name, parsed)
        method_name = completion_data['operation']
        api_params = self._map_command_to_api_params(parsed, completion_data)
        response = self._invoke_api(client, method_name, api_params)
        if response:
            result = self.jmespath.search(completion_data['jp_expr'], response)
            if result:
                return result
        return []

    def _invoke_api(self, client, py_name, api_params):
        try:
            return getattr(client, py_name)(**api_params)
        except Exception:
            # We don't want tracebacks to propagate back out to the user
            # so the best we can do is log the exception.
            LOG.debug("Exception raised when calling %s on client %s",
                      client, py_name, exc_info=True)
            return {}

    def _map_command_to_api_params(self, parsed, completion_data):
        # Right now we don't autogenerate any completion with the 'parameters'
        # key populated, but we will eventually need to handle this once we
        # do so.
        return {}


class BaseCustomServerSideCompleter(ServerSideCompleter):
    _PARAM_NAME = ''
    _COMMAND_NAMES = ''
    _LINEAGE = []

    def __init__(self, client_creator=None):
        self._client_creator = client_creator
        if self._client_creator is None:
            self._client_creator = LazyClientCreator()

    def complete(self, parsed):
        if not self._is_value_for_param(parsed):
            return
        remote_results = self._get_remote_results(parsed)
        completion_results = []
        for remote_result in remote_results:
            if remote_result.startswith(parsed.current_fragment):
                completion_results.append(
                    CompletionResult(
                        remote_result, -len(parsed.current_fragment))
                )
        return completion_results

    def _is_value_for_param(self, parsed):
        return (
            parsed.lineage == self._LINEAGE and
            parsed.current_command in self._COMMAND_NAMES and
            parsed.current_param == self._PARAM_NAME
        )

    def _get_remote_results(self, parsed):
        raise NotImplementedError('_get_remote_results()')
