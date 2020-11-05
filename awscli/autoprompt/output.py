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
import argparse
import io
import re

import jmespath
from botocore.utils import ArgumentGenerator

from awscli.formatter import get_formatter
from awscli.autocomplete.local.fetcher import CliDriverFetcher


class OutputGetter:
    def __init__(self, driver):
        self._cli_driver_fetcher = CliDriverFetcher(driver)
        self._output_formats = driver.arg_table['output'].choices
        self._session = driver.session
        self._cache = {}
        self._current_expression = None

    def get_output(self, parsed):
        operation = ''.join([part.capitalize()
                             for part in parsed.current_command.split('-')])
        operation_model = self._cli_driver_fetcher.get_operation_model(
            parsed.lineage, parsed.current_command, operation)
        if operation_model:
            output_shape = operation_model.output_shape
            if output_shape:
                output = self._get_output(parsed)
                query = self._get_query(parsed)
                return self._get_display(operation, output_shape,
                                         output, query)
        return 'No output'

    def _get_output(self, parsed):
        if parsed.current_param == 'output':
            output = parsed.current_fragment
        else:
            output = parsed.global_params.get('output')
        if output not in self._output_formats:
            output = self._session.get_config_variable('output')
        return output

    def _get_query(self, parsed):
        if parsed.current_param == 'query':
            query = parsed.current_fragment
        else:
            query = parsed.global_params.get('query')
        if query:
            query = re.sub(r'([\{\[])/d+?([\}\]])', '\g<1>\g<2>', query)
        try:
            self._current_expression = jmespath.compile(query)
        except Exception:
            pass
        return self._current_expression

    def _get_display(self, operation, output_shape, output, query):
        args = argparse.Namespace(query=query, color='off')
        argument_generator = ArgumentGenerator(use_member_names=True)
        response = argument_generator.generate_skeleton(output_shape)
        formatter = get_formatter(output, args)
        stream = io.StringIO()
        formatter(operation, response, stream)
        return stream.getvalue().replace('\t', '  ')
