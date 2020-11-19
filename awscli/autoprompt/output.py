# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import logging
import io
import re

import jmespath
from botocore.utils import ArgumentGenerator

from awscli.formatter import get_formatter
from awscli.autocomplete.local.fetcher import CliDriverFetcher


LOG = logging.getLogger(__name__)


class OutputGetter:
    def __init__(self, driver):
        self._cli_driver_fetcher = CliDriverFetcher(driver)
        self._output_formats = driver.arg_table['output'].choices
        self._session = driver.session
        self._current_expression = None

    def get_output(self, parsed):
        operation_model = self._cli_driver_fetcher.get_operation_model(
            parsed.lineage, parsed.current_command)
        if operation_model:
            output_shape = getattr(operation_model, 'output_shape', None)
            if self._shape_has_members(output_shape):
                operation = ''.join(
                    [part.capitalize()
                     for part in parsed.current_command.split('-')]
                )
                output, error_message = self._get_output(parsed)
                if error_message is not None:
                    return error_message
                query, error_message = self._get_query(parsed)
                if error_message is not None:
                    return error_message
                return self._get_display(operation, output_shape,
                                         output, query)
        return 'No output'

    def _shape_has_members(self, shape):
        return shape and (getattr(shape, 'members', False) or
                          getattr(shape, 'member', False))

    def _get_output(self, parsed):
        error_message = None
        if parsed.current_param == 'output':
            if parsed.current_fragment in self._output_formats:
                return parsed.current_fragment, error_message
        session_output = self._session.get_config_variable('output')
        output = parsed.global_params.get('output') or session_output
        if output not in self._output_formats:
            error_message = (
                "Bad value for --output: %s\n\nValid values are: %s" %
                (output, ', '.join(self._output_formats))
            )
        return output, error_message

    def _get_query(self, parsed):
        error_message = None
        if parsed.current_param == 'query':
            query = parsed.current_fragment
        else:
            query = parsed.global_params.get('query')
        if query:
            # Because output example has only 1 element in any list if
            # user enters query like Groups[2] jmespath will return "null"
            # so we change all the numbers in brackets to 0 to keep the output
            # meaningful
            query = re.sub(r'([\{\[])\d+?([\}\]])', '\g<1>0\g<2>', query)
            # In case of incorrect expression we return an error message
            # but we want to do it only in the case expression is really broken
            # and not during user types it so if expression has open bracket
            # with input at the end or trailing dot we remove this part before
            # parsing, for example:
            #
            # for "Groups." we will parse only "Groups"
            # for "Groups.Names[34" we will parse only "Groups.Names"
            query = re.sub(r'([\{\[])[^\]^\}]*$', '', query).strip('.')
        try:
            self._current_expression = jmespath.compile(query)
        except jmespath.exceptions.ParseError as e:
            error_message = "Bad value for --query: %s\n\n%s" % (query, str(e))
        except jmespath.exceptions.EmptyExpressionError:
            self._current_expression = None
        except Exception:
            LOG.debug('Exception caught in OutputGetter: ', exc_info=True)
        return self._current_expression, error_message

    def _get_display(self, operation, output_shape, output, query):
        args = argparse.Namespace(query=query, color='off')
        argument_generator = ArgumentGenerator(use_member_names=True)
        response = argument_generator.generate_skeleton(output_shape)
        formatter = get_formatter(output, args)
        stream = io.StringIO()
        formatter(operation, response, stream)
        return stream.getvalue().replace('\t', '  ')
