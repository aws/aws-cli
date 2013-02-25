# Copyright (c) 2013 Amazon.com, Inc. or its affiliates.  All Rights Reserved
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
import re

import jmespath
from botocore.exceptions import PaginationError


class Paginator(object):
    def __init__(self, operation):
        self._operation = operation
        self._pagination_cfg = operation.pagination
        self._output_tokens = self._get_output_tokens(self._pagination_cfg)
        self._input_token = self._pagination_cfg['py_input_token']

    def _get_output_tokens(self, config):
        output = []
        for config in self._pagination_cfg['output_tokens']:
            output.append(jmespath.compile(config))
        return output

    def paginate(self, endpoint, **kwargs):
        current_kwargs = kwargs
        previous_next_token = None
        while True:
            http_response, parsed = self._operation.call(endpoint,
                                                         **current_kwargs)
            yield http_response, parsed
            next_token = self._get_next_token(parsed)
            if next_token is None:
                break
            if previous_next_token is not None and \
                    previous_next_token == next_token:
                message = ("The same next token was received "
                           "twice: %s" % next_token)
                raise PaginationError(message=message)
            current_kwargs[self._input_token] = next_token
            previous_next_token = next_token

    def _get_next_token(self, parsed):
        for token in self._output_tokens:
            next_token = token.search(parsed)
            if next_token is not None:
                return next_token
