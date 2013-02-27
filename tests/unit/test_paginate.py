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

from tests import unittest
from botocore.paginate import Paginator
from botocore.exceptions import PaginationError
from botocore.operation import Operation

import mock


class TestPagination(unittest.TestCase):
    def setUp(self):
        self.operation = mock.Mock()
        self.paginate_config = {
            'output_tokens': ['NextToken'],
            'py_input_token': 'NextToken',
        }
        self.operation.pagination = self.paginate_config
        self.paginator = Paginator(self.operation)

    def test_no_next_token(self):
        response = {'not_the_next_token': 'foobar'}
        self.operation.call.return_value = None, response
        actual = list(self.paginator.paginate(None))
        self.assertEqual(actual, [(None, {'not_the_next_token': 'foobar'})])

    def test_next_token_in_response(self):
        responses = [(None, {'NextToken': 'token1'}),
                     (None, {'NextToken': 'token2'}),
                     (None, {'not_next_token': 'foo'})]
        self.operation.call.side_effect = responses
        actual = list(self.paginator.paginate(None))
        self.assertEqual(actual, responses)
        # The first call has no next token, the second and third call should
        # have 'token1' and 'token2' respectively.
        self.assertEqual(self.operation.call.call_args_list,
                         [mock.call(None), mock.call(None, NextToken='token1'),
                          mock.call(None, NextToken='token2')])

    def test_any_passed_in_args_are_unmodified(self):
        responses = [(None, {'NextToken': 'token1'}),
                     (None, {'NextToken': 'token2'}),
                     (None, {'not_next_token': 'foo'})]
        self.operation.call.side_effect = responses
        actual = list(self.paginator.paginate(None, Foo='foo', Bar='bar'))
        self.assertEqual(actual, responses)
        self.assertEqual(
            self.operation.call.call_args_list,
            [mock.call(None, Foo='foo', Bar='bar'),
             mock.call(None, Foo='foo', Bar='bar', NextToken='token1'),
             mock.call(None, Foo='foo', Bar='bar', NextToken='token2')])

    def test_exception_raised_if_same_next_token(self):
        responses = [(None, {'NextToken': 'token1'}),
                     (None, {'NextToken': 'token2'}),
                     (None, {'NextToken': 'token2'})]
        self.operation.call.side_effect = responses
        with self.assertRaises(PaginationError):
            list(self.paginator.paginate(None))

    def test_next_tokens_are_lists(self):
        self.operation.pagination = {
            'output_tokens': ['NextToken', 'NextToken2'],
            'py_input_token': 'NextToken',
        }
        self.paginator = Paginator(self.operation)
        # Verify that despite varying between NextToken and NextToken2
        # we still can extract the right next tokens.
        responses = [
            (None, {'NextToken': 'token1'}),
            (None, {'NextToken2': 'token2'}),
            # The first match found wins, so because NextToken is
            # listed before NextToken2 in the 'output_tokens' config,
            # 'token3' is chosen over 'token4'.
            (None, {'NextToken': 'token3', 'NextToken2': 'token4'}),
            (None, {'not_next_token': 'foo'}),
        ]
        self.operation.call.side_effect = responses
        actual = list(self.paginator.paginate(None))
        self.assertEqual(
            self.operation.call.call_args_list,
            [mock.call(None),
             mock.call(None, NextToken='token1'),
             mock.call(None, NextToken='token2'),
             mock.call(None, NextToken='token3'),])

    def test_more_tokens(self):
        # Some pagination configs have a 'more_token' key that
        # indicate whether or not the results are being paginated.
        self.paginate_config = {
            'more_results': 'IsTruncated',
            'output_tokens': ['NextToken'],
            'py_input_token': 'NextToken',
        }
        self.operation.pagination = self.paginate_config
        self.paginator = Paginator(self.operation)
        responses = [
            (None, {'IsTruncated': True, 'NextToken': 'token1'}),
            (None, {'IsTruncated': True, 'NextToken': 'token2'}),
            # The first match found wins, so because NextToken is
            # listed before NextToken2 in the 'output_tokens' config,
            # 'token3' is chosen over 'token4'.
            (None, {'IsTruncated': False, 'NextToken': 'token3'}),
            (None, {'not_next_token': 'foo'}),
        ]
        self.operation.call.side_effect = responses
        list(self.paginator.paginate(None))
        self.assertEqual(
            self.operation.call.call_args_list,
            [mock.call(None),
             mock.call(None, NextToken='token1'),
             mock.call(None, NextToken='token2'),])



class TestPaginatorObjectConstruction(unittest.TestCase):
    def test_pagination_delegates_to_paginator(self):
        paginator_cls = mock.Mock()
        service = mock.Mock()
        service.type = 'json'
        endpoint = mock.Mock()
        op = Operation(service, {'pagination': {'foo': 'bar'}}, paginator_cls)
        op.paginate(endpoint, foo='bar')

        paginator_cls.return_value.paginate.assert_called_with(
            endpoint, foo='bar')

    def test_can_paginate(self):
        op_data = {'pagination': {'foo': 'bar'}}
        op = Operation(None, op_data)
        self.assertTrue(op.can_paginate)

    def test_exception_raised_when_cannot_paginate(self):
        op = Operation(None, {})
        with self.assertRaises(TypeError):
            op.paginate(None)


class TestPaginatorWithPathExpressions(unittest.TestCase):
    def setUp(self):
        self.operation = mock.Mock()
        # This is something we'd see in s3 pagination.
        self.paginate_config = {
            'output_tokens': ['NextMarker',
                              'ListBucketResult.Contents[-1].Key'],
            'py_input_token': 'next_marker',
        }
        self.operation.pagination = self.paginate_config
        self.paginator = Paginator(self.operation)

    def test_s3_list_objects(self):
        responses = [
            (None, {'NextMarker': 'token1'}),
            (None, {'NextMarker': 'token2'}),
            (None, {'not_next_token': 'foo'})]
        self.operation.call.side_effect = responses
        list(self.paginator.paginate(None))
        self.assertEqual(
            self.operation.call.call_args_list,
            [mock.call(None),
             mock.call(None, next_marker='token1'),
             mock.call(None, next_marker='token2'),])

    def test_s3_list_object_complex(self):
        responses = [
            (None, {'NextMarker': 'token1'}),
            (None, {'ListBucketResult': {
                'Contents': [{"Key": "first"}, {"Key": "Last"}]}}),
            (None, {'not_next_token': 'foo'})]
        self.operation.call.side_effect = responses
        list(self.paginator.paginate(None))
        self.assertEqual(
            self.operation.call.call_args_list,
            [mock.call(None),
             mock.call(None, next_marker='token1'),
             mock.call(None, next_marker='Last'),])


if __name__ == '__main__':
    unittest.main()
