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
from itertools import tee
from collections import defaultdict
try:
    from itertools import zip_longest
except ImportError:
    # Python2.x is izip_longest.
    from itertools import izip_longest as zip_longest

try:
    zip
except NameError:
    # Python2.x is izip.
    from itertools import izip as zip

import jmespath
from botocore.exceptions import PaginationError


class Paginator(object):
    def __init__(self, operation):
        self._operation = operation
        self._pagination_cfg = operation.pagination
        self._output_token = self._get_output_tokens(self._pagination_cfg)
        self._input_token = self._get_input_tokens(self._pagination_cfg)
        self._more_results = self._get_more_results_token(self._pagination_cfg)
        self._result_key = self._get_result_key(self._pagination_cfg)

    def _get_output_tokens(self, config):
        output = []
        output_token = config['output_token']
        if not isinstance(output_token, list):
            output_token = [output_token]
        for config in output_token:
            output.append(jmespath.compile(config))
        return output

    def _get_input_tokens(self, config):
        input_token = self._pagination_cfg['py_input_token']
        if not isinstance(input_token, list):
            input_token = [input_token]
        return input_token

    def _get_more_results_token(self, config):
        more_results = config.get('more_results')
        if more_results is not None:
            return jmespath.compile(more_results)

    def _get_result_key(self, config):
        result_key = config.get('result_key')
        if result_key is not None:
            if not isinstance(result_key, list):
                result_key = [result_key]
            return result_key

    def paginate(self, endpoint, **kwargs):
        """Paginate responses to an operation.

        The responses to some operations are too large for a single response.
        When this happens, the service will indicate that there are more
        results in its response.  This method handles the details of how
        to detect when this happens and how to retrieve more results.

        This method returns an iterator.  Each element in the iterator
        is the result of an ``Operation.call`` call, so each element is
        a tuple of (``http_response``, ``parsed_result``).

        """
        return PageIterator(self._operation, self._input_token,
                            self._output_token, self._more_results,
                            self._result_key, endpoint, kwargs)



class PageIterator(object):
    def __init__(self, operation, input_token, output_token, more_results,
                 result_key, endpoint, op_kwargs):
        self._operation = operation
        self._input_token = input_token
        self._output_token = output_token
        self._more_results = more_results
        self._result_key = result_key
        self._endpoint = endpoint
        self._op_kwargs = op_kwargs
        self._http_responses = []

    @property
    def http_responses(self):
        return self._http_responses

    def __iter__(self):
        current_kwargs = self._op_kwargs
        endpoint = self._endpoint
        previous_next_token = None
        while True:
            http_response, parsed = self._operation.call(endpoint,
                                                         **current_kwargs)
            self._http_responses.append(http_response)
            yield http_response, parsed
            next_token = self._get_next_token(parsed)
            if all(t is None for t in next_token):
                break
            if previous_next_token is not None and \
                    previous_next_token == next_token:
                message = ("The same next token was received "
                           "twice: %s" % next_token)
                raise PaginationError(message=message)
            for name, token in zip(self._input_token, next_token):
                current_kwargs[name] = token
            previous_next_token = next_token

    def _get_next_token(self, parsed):
        if self._more_results is not None:
            if not self._more_results.search(parsed):
                return [None]
        next_tokens = []
        for token in self._output_token:
            next_tokens.append(token.search(parsed))
        return next_tokens

    def result_key_iters(self):
        teed_results = tee(self, len(self._result_key))
        return [ResultKeyIterator(i, result_key) for i, result_key
                in zip(teed_results, self._result_key)]

    def build_full_result(self):
        iterators = self.result_key_iters()
        if len(iterators) > 1:
           response = defaultdict(list)
           key_names = [i.result_key for i in iterators]
           for vals in zip_longest(*iterators):
               for k, val in zip(key_names, vals):
                   response[k].append(val)
        else:
            response = list(iterators[0])
        return response


class ResultKeyIterator(object):
    """Iterates over the results of paginated responses."""
    def __init__(self, pages_iterator, result_key):
        self._pages_iterator = pages_iterator
        self.result_key = result_key

    def __iter__(self):
        for _, page in self._pages_iterator:
            for result in page.get(self.result_key, []):
                yield result
