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
        more_results = config.get('more_key')
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
        page_params = self._extract_paging_params(kwargs)
        return PageIterator(self._operation, self._input_token,
                            self._output_token, self._more_results,
                            self._result_key, page_params['max_items'],
                            page_params['starting_token'],
                            endpoint, kwargs)

    def _extract_paging_params(self, kwargs):
        return {
            'max_items': kwargs.pop('max_items', None),
            'starting_token': kwargs.pop('starting_token', None),
        }


class PageIterator(object):
    def __init__(self, operation, input_token, output_token, more_results,
                 result_key, max_items, starting_token, endpoint, op_kwargs):
        self._operation = operation
        self._input_token = input_token
        self._output_token = output_token
        self._more_results = more_results
        self._result_key = result_key
        self._max_items = max_items
        self._starting_token = starting_token
        self._endpoint = endpoint
        self._op_kwargs = op_kwargs
        self._http_responses = []
        self._resume_token = None

    @property
    def http_responses(self):
        return self._http_responses

    @property
    def resume_token(self):
        """Token to specify to resume pagination."""
        return self._resume_token

    @resume_token.setter
    def resume_token(self, value):
        if isinstance(value, list):
            self._resume_token = '___'.join([str(v) for v in value])

    def __iter__(self):
        current_kwargs = self._op_kwargs
        endpoint = self._endpoint
        previous_next_token = None
        next_token = [None for _ in range(len(self._input_token))]
        # The number of items from result_key we've seen so far.
        total_items = 0
        first_request = True
        primary_result_key = self._result_key[0]
        starting_truncation = 0
        self._inject_starting_token(current_kwargs)
        while True:
            http_response, parsed = self._operation.call(endpoint,
                                                         **current_kwargs)
            self._http_responses.append(http_response)
            if first_request:
                # The first request is handled differently.  We could
                # possibly have a resume/starting token that tells us where
                # to index into the retrieved page.
                if self._starting_token is not None:
                    starting_truncation = self._handle_first_request(
                        parsed, primary_result_key, starting_truncation)
                first_request = False
            num_current_response = len(parsed.get(primary_result_key, []))
            truncate_amount = 0
            if self._max_items is not None:
                truncate_amount = (total_items + num_current_response) \
                    - self._max_items
            if truncate_amount > 0:
                self._truncate_response(parsed, primary_result_key,
                                        truncate_amount, starting_truncation,
                                        next_token)
                yield http_response, parsed
                break
            else:
                yield http_response, parsed
                total_items += num_current_response
                next_token = self._get_next_token(parsed)
                if all(t is None for t in next_token):
                    break
                if self._max_items is not None and \
                        total_items == self._max_items:
                    # We're on a page boundary so we can set the current
                    # next token to be the resume token.
                    self.resume_token = next_token
                    break
                if previous_next_token is not None and \
                        previous_next_token == next_token:
                    message = ("The same next token was received "
                               "twice: %s" % next_token)
                    raise PaginationError(message=message)
                self._inject_token_into_kwargs(current_kwargs, next_token)
                previous_next_token = next_token

    def _inject_starting_token(self, op_kwargs):
        # If the user has specified a starting token we need to
        # inject that into the operation's kwargs.
        if self._starting_token is not None:
            # Don't need to do anything special if there is no starting
            # token specified.
            next_token = self._parse_starting_token()[0]
            self._inject_token_into_kwargs(op_kwargs, next_token)

    def _inject_token_into_kwargs(self, op_kwargs, next_token):
        for name, token in zip(self._input_token, next_token):
            if token is None or token == 'None':
                continue
            op_kwargs[name] = token

    def _handle_first_request(self, parsed, primary_result_key,
                              starting_truncation):
        # First we need to slice into the array and only return
        # the truncated amount.
        starting_truncation = self._parse_starting_token()[1]
        parsed[primary_result_key] = parsed[
            primary_result_key][starting_truncation:]
        # We also need to truncate any secondary result keys
        # because they were not truncated in the previous last
        # response.
        for token in self._result_key:
            if token == primary_result_key:
                continue
            parsed[token] = []
        return starting_truncation

    def _truncate_response(self, parsed, primary_result_key, truncate_amount,
                           starting_truncation, next_token):
        original = parsed.get(primary_result_key, [])
        amount_to_keep = len(original) - truncate_amount
        truncated = original[:amount_to_keep]
        parsed[primary_result_key] = truncated
        # The issue here is that even though we know how much we've truncated
        # we need to account for this globally including any starting
        # left truncation. For example:
        # Raw response: [0,1,2,3]
        # Starting index: 1
        # Max items: 1
        # Starting left truncation: [1, 2, 3]
        # End right truncation for max items: [1]
        # However, even though we only kept 1, this is post
        # left truncation so the next starting index should be 2, not 1
        # (left_truncation + amount_to_keep).
        next_token.append(str(amount_to_keep + starting_truncation))
        self.resume_token = next_token

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
        response = {}
        key_names = [i.result_key for i in iterators]
        for key in key_names:
            response[key] = []
        for vals in zip_longest(*iterators):
            for k, val in zip(key_names, vals):
                if val is not None:
                    response[k].append(val)
        if self.resume_token is not None:
            response['NextToken'] = self.resume_token
        return response

    def _parse_starting_token(self):
        if self._starting_token is None:
            return None
        parts = self._starting_token.split('___')
        next_token = []
        index = 0
        if len(parts) == len(self._input_token) + 1:
            try:
                index = int(parts.pop())
            except ValueError:
                raise ValueError("Bad starting token: %s" %
                                 self._starting_token)
        for part in parts:
            if part == 'None':
                next_token.append(None)
            else:
                next_token.append(part)
        return next_token, index


class ResultKeyIterator(object):
    """Iterates over the results of paginated responses."""
    def __init__(self, pages_iterator, result_key):
        self._pages_iterator = pages_iterator
        self.result_key = result_key

    def __iter__(self):
        for _, page in self._pages_iterator:
            for result in page.get(self.result_key, []):
                yield result
