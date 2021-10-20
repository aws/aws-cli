# Copyright 2012-2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

from tests import unittest
from botocore import model
from botocore.paginate import Paginator
from botocore.paginate import PaginatorModel
from botocore.paginate import TokenDecoder
from botocore.paginate import TokenEncoder
from botocore.exceptions import PaginationError
from botocore.compat import six

import mock


def encode_token(token):
    return TokenEncoder().encode(token)


class TestTokenDecoder(unittest.TestCase):
    def setUp(self):
        self.decoder = TokenDecoder()

    def test_decode(self):
        token = 'eyJmb28iOiAiYmFyIn0='
        expected = {'foo': 'bar'}
        self.assertEqual(self.decoder.decode(token), expected)

    def test_decode_with_bytes(self):
        token = (
            'eyJib3RvX2VuY29kZWRfa2V5cyI6IFtbImZvbyJdXSwgImZvbyI6ICJZbUZ5In0='
        )
        expected = {'foo': b'bar'}
        self.assertEqual(self.decoder.decode(token), expected)

    def test_decode_with_nested_bytes(self):
        token = (
            'eyJmb28iOiB7ImJhciI6ICJZbUY2In0sICJib3RvX2VuY29kZWRfa2V5cyI6'
            'IFtbImZvbyIsICJiYXIiXV19'
        )
        expected = {'foo': {'bar': b'baz'}}
        self.assertEqual(self.decoder.decode(token), expected)

    def test_decode_with_listed_bytes(self):
        token = (
            'eyJib3RvX2VuY29kZWRfa2V5cyI6IFtbImZvbyIsICJiYXIiLCAxXV0sICJmb28i'
            'OiB7ImJhciI6IFsiYmF6IiwgIlltbHUiXX19'
        )
        expected = {'foo': {'bar': ['baz', b'bin']}}
        self.assertEqual(self.decoder.decode(token), expected)

    def test_decode_with_multiple_bytes_values(self):
        token = (
            'eyJib3RvX2VuY29kZWRfa2V5cyI6IFtbImZvbyIsICJiaW4iXSwgWyJmb28iLCAi'
            'YmFyIl1dLCAiZm9vIjogeyJiaW4iOiAiWW1GdCIsICJiYXIiOiAiWW1GNiJ9fQ=='
        )
        expected = {'foo': {'bar': b'baz', 'bin': b'bam'}}
        self.assertEqual(self.decoder.decode(token), expected)


class TestPaginatorModel(unittest.TestCase):
    def setUp(self):
        self.paginator_config = {}
        self.paginator_config['pagination'] = {
            'ListFoos': {
                'output_token': 'NextToken',
                'input_token': 'NextToken',
                'result_key': 'Foo'
            }
        }
        self.paginator_model = PaginatorModel(self.paginator_config)

    def test_get_paginator(self):
        paginator_config = self.paginator_model.get_paginator('ListFoos')
        self.assertEqual(
            paginator_config,
            {'output_token': 'NextToken', 'input_token': 'NextToken',
             'result_key': 'Foo'}
        )

    def test_get_paginator_no_exists(self):
        with self.assertRaises(ValueError):
            paginator_config = self.paginator_model.get_paginator('ListBars')


class TestPagination(unittest.TestCase):
    def setUp(self):
        self.method = mock.Mock()
        self.model = mock.Mock()
        self.paginate_config = {
            'output_token': 'NextToken',
            'input_token': 'NextToken',
            'result_key': 'Foo',
        }
        self.paginator = Paginator(self.method, self.paginate_config, self.model)

    def test_result_key_available(self):
        self.assertEqual(
            [rk.expression for rk in self.paginator.result_keys],
            ['Foo']
        )

    def test_no_next_token(self):
        response = {'not_the_next_token': 'foobar'}
        self.method.return_value = response
        actual = list(self.paginator.paginate())
        self.assertEqual(actual, [{'not_the_next_token': 'foobar'}])

    def test_next_token_in_response(self):
        responses = [{'NextToken': 'token1'},
                     {'NextToken': 'token2'},
                     {'not_next_token': 'foo'}]
        self.method.side_effect = responses
        actual = list(self.paginator.paginate())
        self.assertEqual(actual, responses)
        # The first call has no next token, the second and third call should
        # have 'token1' and 'token2' respectively.
        self.assertEqual(self.method.call_args_list,
                         [mock.call(), mock.call(NextToken='token1'),
                          mock.call(NextToken='token2')])

    def test_next_token_is_string(self):
        self.paginate_config = {
            "output_token": "Marker",
            "input_token": "Marker",
            "result_key": "Users",
            "limit_key": "MaxKeys",
        }
        self.paginator = Paginator(self.method, self.paginate_config, self.model)
        responses = [
            {"Users": ["User1"], "Marker": "m1"},
            {"Users": ["User2"], "Marker": "m2"},
            {"Users": ["User3"]}
        ]
        self.method.side_effect = responses
        result = self.paginator.paginate(PaginationConfig={'MaxItems': 1})
        result = result.build_full_result()
        token = result.get('NextToken')
        self.assertIsInstance(token, six.string_types)

    def test_any_passed_in_args_are_unmodified(self):
        responses = [{'NextToken': 'token1'},
                     {'NextToken': 'token2'},
                     {'not_next_token': 'foo'}]
        self.method.side_effect = responses
        actual = list(self.paginator.paginate(Foo='foo', Bar='bar'))
        self.assertEqual(actual, responses)
        self.assertEqual(
            self.method.call_args_list,
            [mock.call(Foo='foo', Bar='bar'),
             mock.call(Foo='foo', Bar='bar', NextToken='token1'),
             mock.call(Foo='foo', Bar='bar', NextToken='token2')])

    def test_exception_raised_if_same_next_token(self):
        responses = [{'NextToken': 'token1'},
                     {'NextToken': 'token2'},
                     {'NextToken': 'token2'}]
        self.method.side_effect = responses
        with self.assertRaises(PaginationError):
            list(self.paginator.paginate())

    def test_next_token_with_or_expression(self):
        self.pagination_config = {
            'output_token': 'NextToken || NextToken2',
            'input_token': 'NextToken',
            'result_key': 'Foo',
        }
        self.paginator = Paginator(self.method, self.pagination_config, self.model)
        # Verify that despite varying between NextToken and NextToken2
        # we still can extract the right next tokens.
        responses = [
            {'NextToken': 'token1'},
            {'NextToken2': 'token2'},
            # The first match found wins, so because NextToken is
            # listed before NextToken2 in the 'output_tokens' config,
            # 'token3' is chosen over 'token4'.
            {'NextToken': 'token3', 'NextToken2': 'token4'},
            {'not_next_token': 'foo'},
        ]
        self.method.side_effect = responses
        list(self.paginator.paginate())
        self.assertEqual(
            self.method.call_args_list,
            [mock.call(),
             mock.call(NextToken='token1'),
             mock.call(NextToken='token2'),
             mock.call(NextToken='token3')])

    def test_more_tokens(self):
        # Some pagination configs have a 'more_token' key that
        # indicate whether or not the results are being paginated.
        self.paginate_config = {
            'more_results': 'IsTruncated',
            'output_token': 'NextToken',
            'input_token': 'NextToken',
            'result_key': 'Foo',
        }
        self.paginator = Paginator(self.method, self.paginate_config, self.model)
        responses = [
            {'Foo': [1], 'IsTruncated': True, 'NextToken': 'token1'},
            {'Foo': [2], 'IsTruncated': True, 'NextToken': 'token2'},
            {'Foo': [3], 'IsTruncated': False, 'NextToken': 'token3'},
            {'Foo': [4], 'not_next_token': 'foo'},
        ]
        self.method.side_effect = responses
        list(self.paginator.paginate())
        self.assertEqual(
            self.method.call_args_list,
            [mock.call(),
             mock.call(NextToken='token1'),
             mock.call(NextToken='token2')])

    def test_more_tokens_is_path_expression(self):
        self.paginate_config = {
            'more_results': 'Foo.IsTruncated',
            'output_token': 'NextToken',
            'input_token': 'NextToken',
            'result_key': 'Bar',
        }
        self.paginator = Paginator(self.method, self.paginate_config, self.model)
        responses = [
            {'Foo': {'IsTruncated': True}, 'NextToken': 'token1'},
            {'Foo': {'IsTruncated': False}, 'NextToken': 'token2'},
        ]
        self.method.side_effect = responses
        list(self.paginator.paginate())
        self.assertEqual(
            self.method.call_args_list,
            [mock.call(),
             mock.call(NextToken='token1')])

    def test_page_size(self):
        self.paginate_config = {
            "output_token": "Marker",
            "input_token": "Marker",
            "result_key": "Users",
            "limit_key": "MaxKeys",
        }
        self.paginator = Paginator(self.method, self.paginate_config, self.model)
        responses = [
            {"Users": ["User1"], "Marker": "m1"},
            {"Users": ["User2"], "Marker": "m2"},
            {"Users": ["User3"]},
        ]
        self.method.side_effect = responses
        users = []
        for page in self.paginator.paginate(PaginationConfig={'PageSize': 1}):
            users += page['Users']
        self.assertEqual(
            self.method.call_args_list,
            [mock.call(MaxKeys=1),
             mock.call(Marker='m1', MaxKeys=1),
             mock.call(Marker='m2', MaxKeys=1)]
        )

    def test_with_empty_markers(self):
        responses = [
            {"Users": ["User1"], "Marker": ""},
            {"Users": ["User1"], "Marker": ""},
            {"Users": ["User1"], "Marker": ""}
        ]
        self.method.side_effect = responses
        users = []
        for page in self.paginator.paginate():
            users += page['Users']
        # We want to stop paginating if the next token is empty.
        self.assertEqual(
            self.method.call_args_list,
            [mock.call()]
        )
        self.assertEqual(users, ['User1'])

    def test_build_full_result_with_single_key(self):
        self.paginate_config = {
            "output_token": "Marker",
            "input_token": "Marker",
            "result_key": "Users",
            "limit_key": "MaxKeys",
        }
        self.paginator = Paginator(self.method, self.paginate_config, self.model)
        responses = [
            {"Users": ["User1"], "Marker": "m1"},
            {"Users": ["User2"], "Marker": "m2"},
            {"Users": ["User3"]}
        ]
        self.method.side_effect = responses
        pages = self.paginator.paginate()
        complete = pages.build_full_result()
        self.assertEqual(complete, {'Users': ['User1', 'User2', 'User3']})

    def test_build_multiple_results(self):
        self.paginate_config = {
            "output_token": "Marker",
            "input_token": "Marker",
            "result_key": "Users",
            "limit_key": "MaxKeys",
        }
        self.paginator = Paginator(self.method, self.paginate_config, self.model)

        max_items = 3
        page_size = 2

        responses = [
            {"Users": ["User1", "User2"], "Marker": "m1"},
            {"Users": ["User3", "User4"], "Marker": "m2"},
            {"Users": ["User3", "User4"], "Marker": "m2"},
            {"Users": ["User5", "User6", "User7"], "Marker": "m3"},
        ]
        self.method.side_effect = responses

        pages = self.paginator.paginate(
            PaginationConfig={
                'PageSize': page_size,
                'MaxItems': max_items
            }
        )
        result = pages.build_full_result()

        pages = self.paginator.paginate(
            PaginationConfig={
                'MaxItems': max_items,
                'PageSize': page_size,
                'StartingToken': result['NextToken']
            }
        )
        result = pages.build_full_result()

        expected_token = encode_token({
            'Marker': 'm2',
            'boto_truncate_amount': 2,
        })
        self.assertEqual(expected_token, result['NextToken'])


class TestPaginatorPageSize(unittest.TestCase):
    def setUp(self):
        self.method = mock.Mock()
        self.model = mock.Mock()
        self.paginate_config = {
            "output_token": "Marker",
            "input_token": "Marker",
            "result_key": ["Users", "Groups"],
            'limit_key': 'MaxKeys',
        }
        self.paginator = Paginator(self.method, self.paginate_config, self.model)
        self.endpoint = mock.Mock()

    def test_no_page_size(self):
        kwargs = {'arg1': 'foo', 'arg2': 'bar'}
        ref_kwargs = {'arg1': 'foo', 'arg2': 'bar'}
        pages = self.paginator.paginate(**kwargs)
        pages._inject_starting_params(kwargs)
        self.assertEqual(kwargs, ref_kwargs)

    def test_page_size(self):
        kwargs = {'arg1': 'foo', 'arg2': 'bar',
                  'PaginationConfig': {'PageSize': 5}}
        extracted_kwargs = {'arg1': 'foo', 'arg2': 'bar'}
        # Note that ``MaxKeys`` in ``setUp()`` is the parameter used for
        # the page size for pagination.
        ref_kwargs = {'arg1': 'foo', 'arg2': 'bar', 'MaxKeys': 5}
        pages = self.paginator.paginate(**kwargs)
        pages._inject_starting_params(extracted_kwargs)
        self.assertEqual(extracted_kwargs, ref_kwargs)

    def test_page_size_incorrectly_provided(self):
        kwargs = {'arg1': 'foo', 'arg2': 'bar',
                  'PaginationConfig': {'PageSize': 5}}
        del self.paginate_config['limit_key']
        paginator = Paginator(self.method, self.paginate_config, self.model)

        with self.assertRaises(PaginationError):
            paginator.paginate(**kwargs)


class TestPaginatorWithPathExpressions(unittest.TestCase):
    def setUp(self):
        self.method = mock.Mock()
        self.model = mock.Mock()
        # This is something we'd see in s3 pagination.
        self.paginate_config = {
            'output_token': [
                'NextMarker || ListBucketResult.Contents[-1].Key'],
            'input_token': 'next_marker',
            'result_key': 'Contents',
        }
        self.paginator = Paginator(self.method, self.paginate_config, self.model)

    def test_s3_list_objects(self):
        responses = [
            {'NextMarker': 'token1'},
            {'NextMarker': 'token2'},
            {'not_next_token': 'foo'}]
        self.method.side_effect = responses
        list(self.paginator.paginate())
        self.assertEqual(
            self.method.call_args_list,
            [mock.call(),
             mock.call(next_marker='token1'),
             mock.call(next_marker='token2')])

    def test_s3_list_object_complex(self):
        responses = [
            {'NextMarker': 'token1'},
            {'ListBucketResult': {
                'Contents': [{"Key": "first"}, {"Key": "Last"}]}},
            {'not_next_token': 'foo'}]
        self.method.side_effect = responses
        list(self.paginator.paginate())
        self.assertEqual(
            self.method.call_args_list,
            [mock.call(),
             mock.call(next_marker='token1'),
             mock.call(next_marker='Last')])


class TestBinaryTokens(unittest.TestCase):
    def setUp(self):
        self.method = mock.Mock()
        self.model = mock.Mock()
        self.paginate_config = {
            "output_token": "Marker",
            "input_token": "Marker",
            "result_key": "Users"
        }
        self.paginator = Paginator(self.method, self.paginate_config, self.model)

    def test_build_full_result_with_bytes(self):
        responses = [
            {"Users": ["User1", "User2"], "Marker": b'\xff'},
            {"Users": ["User3", "User4"], "Marker": b'\xfe'},
            {"Users": ["User5"]}
        ]
        self.method.side_effect = responses
        pages = self.paginator.paginate(PaginationConfig={'MaxItems': 3})
        complete = pages.build_full_result()
        expected_token = encode_token({
            "Marker": b'\xff', "boto_truncate_amount": 1,
        })
        expected_response = {
            "Users": ["User1", "User2", "User3"],
            "NextToken": expected_token
        }
        self.assertEqual(complete, expected_response)

    def test_build_full_result_with_nested_bytes(self):
        responses = [
            {"Users": ["User1", "User2"], "Marker": {'key': b'\xff'}},
            {"Users": ["User3", "User4"], "Marker": {'key': b'\xfe'}},
            {"Users": ["User5"]}
        ]
        self.method.side_effect = responses
        pages = self.paginator.paginate(PaginationConfig={'MaxItems': 3})
        complete = pages.build_full_result()
        expected_token = encode_token({
            "Marker": {'key': b'\xff'}, "boto_truncate_amount": 1,
        })
        expected_response = {
            "Users": ["User1", "User2", "User3"],
            "NextToken": expected_token
        }
        self.assertEqual(complete, expected_response)

    def test_build_full_result_with_listed_bytes(self):
        responses = [
            {"Users": ["User1", "User2"], "Marker": {'key': ['foo', b'\xff']}},
            {"Users": ["User3", "User4"], "Marker": {'key': ['foo', b'\xfe']}},
            {"Users": ["User5"]}
        ]
        self.method.side_effect = responses
        pages = self.paginator.paginate(PaginationConfig={'MaxItems': 3})
        complete = pages.build_full_result()
        expected_token = encode_token({
            "Marker": {'key': ['foo', b'\xff']}, "boto_truncate_amount": 1,
        })
        expected_response = {
            "Users": ["User1", "User2", "User3"],
            "NextToken": expected_token
        }
        self.assertEqual(complete, expected_response)

    def test_build_full_result_with_multiple_bytes_values(self):
        responses = [
            {
                "Users": ["User1", "User2"],
                "Marker": {'key': b'\xff', 'key2': b'\xef'}
            },
            {
                "Users": ["User3", "User4"],
                "Marker": {'key': b'\xfe', 'key2': b'\xee'}
            },
            {
                "Users": ["User5"]
            }
        ]
        self.method.side_effect = responses
        pages = self.paginator.paginate(PaginationConfig={'MaxItems': 3})
        complete = pages.build_full_result()
        expected_token = encode_token({
            "Marker": {'key': b'\xff', 'key2': b'\xef'},
            "boto_truncate_amount": 1,
        })
        expected_response = {
            "Users": ["User1", "User2", "User3"],
            "NextToken": expected_token
        }
        self.assertEqual(complete, expected_response)

    def test_resume_with_bytes(self):
        responses = [
            {"Users": ["User3", "User4"], "Marker": b'\xfe'},
            {"Users": ["User5"]}
        ]
        self.method.side_effect = responses
        starting_token = encode_token({
            "Marker": b'\xff', "boto_truncate_amount": 1,
        })
        pages = self.paginator.paginate(
            PaginationConfig={'StartingToken': starting_token})
        complete = pages.build_full_result()
        expected_response = {
            "Users": ["User4", "User5"]
        }
        self.assertEqual(complete, expected_response)
        self.method.assert_any_call(Marker=b'\xff')

    def test_resume_with_nested_bytes(self):
        responses = [
            {"Users": ["User3", "User4"], "Marker": {'key': b'\xfe'}},
            {"Users": ["User5"]}
        ]
        self.method.side_effect = responses
        starting_token = encode_token({
            "Marker": {'key': b'\xff'}, "boto_truncate_amount": 1,
        })
        pages = self.paginator.paginate(
            PaginationConfig={'StartingToken': starting_token})
        complete = pages.build_full_result()
        expected_response = {
            "Users": ["User4", "User5"]
        }
        self.assertEqual(complete, expected_response)
        self.method.assert_any_call(Marker={'key': b'\xff'})

    def test_resume_with_listed_bytes(self):
        responses = [
            {"Users": ["User3", "User4"], "Marker": {'key': ['bar', b'\xfe']}},
            {"Users": ["User5"]}
        ]
        self.method.side_effect = responses
        starting_token = encode_token({
            "Marker": {'key': ['foo', b'\xff']}, "boto_truncate_amount": 1,
        })
        pages = self.paginator.paginate(
            PaginationConfig={'StartingToken': starting_token})
        complete = pages.build_full_result()
        expected_response = {
            "Users": ["User4", "User5"]
        }
        self.assertEqual(complete, expected_response)
        self.method.assert_any_call(Marker={'key': ['foo', b'\xff']})

    def test_resume_with_multiple_bytes_values(self):
        responses = [
            {
                "Users": ["User3", "User4"],
                "Marker": {'key': b'\xfe', 'key2': b'\xee'}
            },
            {
                "Users": ["User5"]
            }
        ]
        self.method.side_effect = responses
        starting_token = encode_token({
            "Marker": {'key': b'\xff', 'key2': b'\xef'},
            "boto_truncate_amount": 1,
        })
        pages = self.paginator.paginate(
            PaginationConfig={'StartingToken': starting_token})
        complete = pages.build_full_result()
        expected_response = {
            "Users": ["User4", "User5"]
        }
        self.assertEqual(complete, expected_response)
        self.method.assert_any_call(Marker={'key': b'\xfe', 'key2': b'\xee'})


class TestMultipleTokens(unittest.TestCase):
    def setUp(self):
        self.method = mock.Mock()
        self.model = mock.Mock()
        # This is something we'd see in s3 pagination.
        self.paginate_config = {
            "output_token": ["ListBucketResults.NextKeyMarker",
                             "ListBucketResults.NextUploadIdMarker"],
            "input_token": ["key_marker", "upload_id_marker"],
            "result_key": 'Foo',
        }
        self.paginator = Paginator(self.method, self.paginate_config, self.model)

    def test_s3_list_multipart_uploads(self):
        responses = [
            {"Foo": [1], "ListBucketResults": {"NextKeyMarker": "key1",
                                               "NextUploadIdMarker": "up1"}},
            {"Foo": [2], "ListBucketResults": {"NextKeyMarker": "key2",
                                               "NextUploadIdMarker": "up2"}},
            {"Foo": [3], "ListBucketResults": {"NextKeyMarker": "key3",
                                               "NextUploadIdMarker": "up3"}},
            {}
        ]
        self.method.side_effect = responses
        list(self.paginator.paginate())
        self.assertEqual(
            self.method.call_args_list,
            [mock.call(),
             mock.call(key_marker='key1', upload_id_marker='up1'),
             mock.call(key_marker='key2', upload_id_marker='up2'),
             mock.call(key_marker='key3', upload_id_marker='up3'),
             ])


class TestOptionalTokens(unittest.TestCase):
    """
    Tests a paginator with an optional output token.

    The Route53 ListResourceRecordSets paginator includes three output tokens,
    one of which only appears in certain records. If this gets left in the
    request params from a previous page, the API will skip over a record.

    """
    def setUp(self):
        self.method = mock.Mock()
        self.model = mock.Mock()
        # This is based on Route53 pagination.
        self.paginate_config = {
            "output_token": ["NextRecordName",
                             "NextRecordType",
                             "NextRecordIdentifier"],
            "input_token": ["StartRecordName",
                            "StartRecordType",
                            "StartRecordIdentifier"],
            "result_key": 'Foo',
        }
        self.paginator = Paginator(self.method, self.paginate_config, self.model)

    def test_clean_token(self):
        responses = [
            {"Foo": [1],
             "IsTruncated": True,
             "NextRecordName": "aaa.example.com",
             "NextRecordType": "A",
             "NextRecordIdentifier": "id"},
            {"Foo": [2],
             "IsTruncated": True,
             "NextRecordName": "bbb.example.com",
             "NextRecordType": "A"},
            {"Foo": [3],
             "IsTruncated": False},
        ]
        self.method.side_effect = responses
        list(self.paginator.paginate())
        self.assertEqual(
            self.method.call_args_list,
            [mock.call(),
             mock.call(StartRecordName='aaa.example.com', StartRecordType='A',
                       StartRecordIdentifier='id'),
             mock.call(StartRecordName='bbb.example.com', StartRecordType='A')
             ])


class TestKeyIterators(unittest.TestCase):
    def setUp(self):
        self.method = mock.Mock()
        self.model = mock.Mock()
        # This is something we'd see in s3 pagination.
        self.paginate_config = {
            "output_token": "Marker",
            "input_token": "Marker",
            "result_key": "Users"
        }
        self.paginator = Paginator(self.method, self.paginate_config, self.model)

    def test_result_key_iters(self):
        responses = [
            {"Users": ["User1"], "Marker": "m1"},
            {"Users": ["User2"], "Marker": "m2"},
            {"Users": ["User3"]},
        ]
        self.method.side_effect = responses
        pages = self.paginator.paginate()
        iterators = pages.result_key_iters()
        self.assertEqual(len(iterators), 1)
        self.assertEqual(list(iterators[0]),
                         ["User1", "User2", "User3"])

    def test_build_full_result_with_single_key(self):
        responses = [
            {"Users": ["User1"], "Marker": "m1"},
            {"Users": ["User2"], "Marker": "m2"},
            {"Users": ["User3"]},
        ]
        self.method.side_effect = responses
        pages = self.paginator.paginate()
        complete = pages.build_full_result()
        self.assertEqual(complete, {'Users': ['User1', 'User2', 'User3']})

    def test_max_items_can_be_specified(self):
        paginator = Paginator(self.method, self.paginate_config, self.model)
        responses = [
            {"Users": ["User1"], "Marker": "m1"},
            {"Users": ["User2"], "Marker": "m2"},
            {"Users": ["User3"]},
        ]
        self.method.side_effect = responses
        expected_token = encode_token({"Marker": "m1"})
        self.assertEqual(
            paginator.paginate(
                PaginationConfig={'MaxItems': 1}).build_full_result(),
            {'Users': ['User1'], 'NextToken': expected_token})

    def test_max_items_as_strings(self):
        # Some services (route53) model MaxItems as a string type.
        # We need to be able to handle this case.
        paginator = Paginator(self.method, self.paginate_config, self.model)
        responses = [
            {"Users": ["User1"], "Marker": "m1"},
            {"Users": ["User2"], "Marker": "m2"},
            {"Users": ["User3"]},
        ]
        self.method.side_effect = responses
        expected_token = encode_token({"Marker": "m1"})
        self.assertEqual(
            # Note MaxItems is a string here.
            paginator.paginate(
                PaginationConfig={'MaxItems': '1'}).build_full_result(),
            {'Users': ['User1'], 'NextToken': expected_token})

    def test_next_token_on_page_boundary(self):
        paginator = Paginator(self.method, self.paginate_config, self.model)
        responses = [
            {"Users": ["User1"], "Marker": "m1"},
            {"Users": ["User2"], "Marker": "m2"},
            {"Users": ["User3"]},
        ]
        self.method.side_effect = responses
        expected_token = encode_token({"Marker": "m2"})
        self.assertEqual(
            paginator.paginate(
                PaginationConfig={'MaxItems': 2}).build_full_result(),
            {'Users': ['User1', 'User2'], 'NextToken': expected_token})

    def test_max_items_can_be_specified_truncates_response(self):
        # We're saying we only want 4 items, but notice that the second
        # page of results returns users 4-6 so we have to truncated
        # part of that second page.
        paginator = Paginator(self.method, self.paginate_config, self.model)
        responses = [
            {"Users": ["User1", "User2", "User3"], "Marker": "m1"},
            {"Users": ["User4", "User5", "User6"], "Marker": "m2"},
            {"Users": ["User7"]},
        ]
        self.method.side_effect = responses
        expected_token = encode_token(
            {"Marker": "m1", "boto_truncate_amount": 1})
        self.assertEqual(
            paginator.paginate(
                PaginationConfig={'MaxItems': 4}).build_full_result(),
            {'Users': ['User1', 'User2', 'User3', 'User4'],
             'NextToken': expected_token})

    def test_resume_next_marker_mid_page(self):
        # This is a simulation of picking up from the response
        # from test_MaxItems_can_be_specified_truncates_response
        # We got the first 4 users, when we pick up we should get
        # User5 - User7.
        paginator = Paginator(self.method, self.paginate_config, self.model)
        responses = [
            {"Users": ["User4", "User5", "User6"], "Marker": "m2"},
            {"Users": ["User7"]},
        ]
        self.method.side_effect = responses
        starting_token = encode_token(
            {"Marker": "m1", "boto_truncate_amount": 1})
        pagination_config = {'StartingToken': starting_token}
        self.assertEqual(
            paginator.paginate(
                PaginationConfig=pagination_config).build_full_result(),
            {'Users': ['User5', 'User6', 'User7']})
        self.assertEqual(
            self.method.call_args_list,
            [mock.call(Marker='m1'),
             mock.call(Marker='m2')])

    def test_max_items_exceeds_actual_amount(self):
        # Because MaxItems=10 > number of users (3), we should just return
        # all of the users.
        paginator = Paginator(self.method, self.paginate_config, self.model)
        responses = [
            {"Users": ["User1"], "Marker": "m1"},
            {"Users": ["User2"], "Marker": "m2"},
            {"Users": ["User3"]},
        ]
        self.method.side_effect = responses
        self.assertEqual(
            paginator.paginate(
                PaginationConfig={'MaxItems': 10}).build_full_result(),
            {'Users': ['User1', 'User2', 'User3']})

    def test_bad_input_tokens(self):
        responses = [
            {"Users": ["User1"], "Marker": "m1"},
            {"Users": ["User2"], "Marker": "m2"},
            {"Users": ["User3"]},
        ]
        self.method.side_effect = responses
        with self.assertRaisesRegex(ValueError, 'Bad starting token'):
            pagination_config = {'StartingToken': 'does___not___work'}
            self.paginator.paginate(
                PaginationConfig=pagination_config).build_full_result()


class TestMultipleResultKeys(unittest.TestCase):
    def setUp(self):
        self.method = mock.Mock()
        self.model = mock.Mock()
        # This is something we'd see in s3 pagination.
        self.paginate_config = {
            "output_token": "Marker",
            "input_token": "Marker",
            "result_key": ["Users", "Groups"],
        }
        self.paginator = Paginator(self.method, self.paginate_config, self.model)

    def test_build_full_result_with_multiple_result_keys(self):
        responses = [
            {"Users": ["User1"], "Groups": ["Group1"], "Marker": "m1"},
            {"Users": ["User2"], "Groups": ["Group2"], "Marker": "m2"},
            {"Users": ["User3"], "Groups": ["Group3"]},
        ]
        self.method.side_effect = responses
        pages = self.paginator.paginate()
        complete = pages.build_full_result()
        self.assertEqual(complete,
                         {"Users": ['User1', 'User2', 'User3'],
                          "Groups": ['Group1', 'Group2', 'Group3']})

    def test_build_full_result_with_different_length_result_keys(self):
        responses = [
            {"Users": ["User1"], "Groups": ["Group1"], "Marker": "m1"},
            # Then we stop getting "Users" output, but we get more "Groups"
            {"Users": [], "Groups": ["Group2"], "Marker": "m2"},
            {"Users": [], "Groups": ["Group3"]},
        ]
        self.method.side_effect = responses
        pages = self.paginator.paginate()
        complete = pages.build_full_result()
        self.assertEqual(complete,
                         {"Users": ['User1'],
                          "Groups": ['Group1', 'Group2', 'Group3']})

    def test_build_full_result_with_zero_length_result_key(self):
        responses = [
            # In this case the 'Users' key is always empty but we should
            # have a 'Users' key in the output, it should just have an
            # empty list for a value.
            {"Users": [], "Groups": ["Group1"], "Marker": "m1"},
            {"Users": [], "Groups": ["Group2"], "Marker": "m2"},
            {"Users": [], "Groups": ["Group3"]},
        ]
        self.method.side_effect = responses
        pages = self.paginator.paginate()
        complete = pages.build_full_result()
        self.assertEqual(complete,
                         {"Users": [],
                          "Groups": ['Group1', 'Group2', 'Group3']})

    def test_build_result_with_secondary_keys(self):
        responses = [
            {"Users": ["User1", "User2"],
             "Groups": ["Group1", "Group2"],
             "Marker": "m1"},
            {"Users": ["User3"], "Groups": ["Group3"], "Marker": "m2"},
            {"Users": ["User4"], "Groups": ["Group4"]},
        ]
        self.method.side_effect = responses
        pages = self.paginator.paginate(
            PaginationConfig={'MaxItems': 1})
        complete = pages.build_full_result()
        expected_token = encode_token(
            {"Marker": None, "boto_truncate_amount": 1})
        self.assertEqual(complete,
                         {"Users": ["User1"], "Groups": ["Group1", "Group2"],
                          "NextToken": expected_token})

    def test_resume_with_secondary_keys(self):
        # This is simulating a continutation of the previous test,
        # test_build_result_with_secondary_keys.  We use the
        # token specified in the response "None___1" to continue where we
        # left off.
        responses = [
            {"Users": ["User1", "User2"],
             "Groups": ["Group1", "Group2"],
             "Marker": "m1"},
            {"Users": ["User3"], "Groups": ["Group3"], "Marker": "m2"},
            {"Users": ["User4"], "Groups": ["Group4"]},
        ]
        self.method.side_effect = responses
        starting_token = encode_token(
            {"Marker": None, "boto_truncate_amount": 1})
        pages = self.paginator.paginate(
            PaginationConfig={'MaxItems': 1,
                              'StartingToken': starting_token})
        complete = pages.build_full_result()
        # Note that the secondary keys ("Groups") are all truncated because
        # they were in the original (first) response.
        expected_token = encode_token({"Marker": "m1"})
        self.assertEqual(complete,
                         {"Users": ["User2"], "Groups": [],
                          "NextToken": expected_token})

    def test_resume_with_secondary_result_as_string(self):
        self.method.return_value = {"Users": ["User1", "User2"], "Groups": "a"}
        starting_token = encode_token(
            {"Marker": None, "boto_truncate_amount": 1})
        pages = self.paginator.paginate(
            PaginationConfig={'MaxItems': 1, 'StartingToken': starting_token})
        complete = pages.build_full_result()
        # Note that the secondary keys ("Groups") becomes empty string because
        # they were in the original (first) response.
        self.assertEqual(complete, {"Users": ["User2"], "Groups": ""})

    def test_resume_with_secondary_result_as_integer(self):
        self.method.return_value = {"Users": ["User1", "User2"], "Groups": 123}
        starting_token = encode_token(
            {"Marker": None, "boto_truncate_amount": 1})
        pages = self.paginator.paginate(
            PaginationConfig={'MaxItems': 1, 'StartingToken': starting_token})
        complete = pages.build_full_result()
        # Note that the secondary keys ("Groups") becomes zero because
        # they were in the original (first) response.
        self.assertEqual(complete, {"Users": ["User2"], "Groups": 0})


class TestMultipleInputKeys(unittest.TestCase):
    def setUp(self):
        self.method = mock.Mock()
        self.model = mock.Mock()
        # Probably the most complicated example we'll see:
        # multiple input/output/result keys.
        self.paginate_config = {
            "output_token": ["Marker1", "Marker2"],
            "input_token": ["InMarker1", "InMarker2"],
            "result_key": ["Users", "Groups"],
        }
        self.paginator = Paginator(self.method, self.paginate_config, self.model)

    def test_build_full_result_with_multiple_input_keys(self):
        responses = [
            {"Users": ["User1", "User2"], "Groups": ["Group1"],
             "Marker1": "m1", "Marker2": "m2"},
            {"Users": ["User3", "User4"], "Groups": ["Group2"],
             "Marker1": "m3", "Marker2": "m4"},
            {"Users": ["User5"], "Groups": ["Group3"]}
        ]
        self.method.side_effect = responses
        pages = self.paginator.paginate(
            PaginationConfig={'MaxItems': 3})
        complete = pages.build_full_result()
        expected_token = encode_token(
            {"InMarker1": "m1", "InMarker2": "m2", "boto_truncate_amount": 1})
        self.assertEqual(complete,
                         {"Users": ['User1', 'User2', 'User3'],
                          "Groups": ['Group1', 'Group2'],
                          "NextToken": expected_token})

    def test_resume_with_multiple_input_keys(self):
        responses = [
            {"Users": ["User3", "User4"], "Groups": ["Group2"],
             "Marker1": "m3", "Marker2": "m4"},
            {"Users": ["User5"], "Groups": ["Group3"]},
        ]
        self.method.side_effect = responses
        starting_token = encode_token(
            {"InMarker1": "m1", "InMarker2": "m2", "boto_truncate_amount": 1})
        pages = self.paginator.paginate(
            PaginationConfig={'MaxItems': 1,
                              'StartingToken': starting_token})
        complete = pages.build_full_result()
        expected_token = encode_token(
            {"InMarker1": "m3", "InMarker2": "m4"})
        self.assertEqual(complete,
                         {"Users": ['User4'],
                          "Groups": [],
                          "NextToken": expected_token})
        self.assertEqual(
            self.method.call_args_list,
            [mock.call(InMarker1='m1', InMarker2='m2')])

    def test_resume_encounters_an_empty_payload(self):
        response = {"not_a_result_key": "it happens in some service"}
        self.method.return_value = response
        starting_token = encode_token(
            {"Marker": None, "boto_truncate_amount": 1})
        complete = self.paginator \
            .paginate(PaginationConfig={'StartingToken': starting_token}) \
            .build_full_result()
        self.assertEqual(complete, {})

    def test_result_key_exposed_on_paginator(self):
        self.assertEqual(
            [rk.expression for rk in self.paginator.result_keys],
            ['Users', 'Groups']
        )

    def test_result_key_exposed_on_page_iterator(self):
        pages = self.paginator.paginate(MaxItems=3)
        self.assertEqual(
            [rk.expression for rk in pages.result_keys],
            ['Users', 'Groups']
        )


class TestExpressionKeyIterators(unittest.TestCase):
    def setUp(self):
        self.method = mock.Mock()
        self.model = mock.Mock()
        # This is something like what we'd see in RDS.
        self.paginate_config = {
            "input_token": "Marker",
            "output_token": "Marker",
            "limit_key": "MaxRecords",
            "result_key": "EngineDefaults.Parameters"
        }
        self.paginator = Paginator(self.method, self.paginate_config, self.model)
        self.responses = [
            {"EngineDefaults": {"Parameters": ["One", "Two"]},
             "Marker": "m1"},
            {"EngineDefaults": {"Parameters": ["Three", "Four"]},
             "Marker": "m2"},
            {"EngineDefaults": {"Parameters": ["Five"]}}
        ]

    def test_result_key_iters(self):
        self.method.side_effect = self.responses
        pages = self.paginator.paginate()
        iterators = pages.result_key_iters()
        self.assertEqual(len(iterators), 1)
        self.assertEqual(list(iterators[0]),
                         ['One', 'Two', 'Three', 'Four', 'Five'])

    def test_build_full_result_with_single_key(self):
        self.method.side_effect = self.responses
        pages = self.paginator.paginate()
        complete = pages.build_full_result()
        self.assertEqual(complete, {
            'EngineDefaults': {
                'Parameters': ['One', 'Two', 'Three', 'Four', 'Five']
            },
        })


class TestIncludeResultKeys(unittest.TestCase):
    def setUp(self):
        self.method = mock.Mock()
        self.model = mock.Mock()
        self.paginate_config = {
            'output_token': 'Marker',
            'input_token': 'Marker',
            'result_key': ['ResultKey', 'Count', 'Log'],
        }
        self.paginator = Paginator(self.method, self.paginate_config, self.model)

    def test_different_kinds_of_result_key(self):
        self.method.side_effect = [
            {'ResultKey': ['a'], 'Count': 1, 'Log': 'x', 'Marker': 'a'},
            {'not_a_result_key': 'this page will be ignored', 'Marker': '_'},
            {'ResultKey': ['b', 'c'], 'Count': 2, 'Log': 'y', 'Marker': 'b'},
            {'ResultKey': ['d', 'e', 'f'], 'Count': 3, 'Log': 'z'},
        ]
        pages = self.paginator.paginate()
        expected = {
            'ResultKey': ['a', 'b', 'c', 'd', 'e', 'f'],
            'Count': 6,
            'Log': 'xyz',
        }
        self.assertEqual(pages.build_full_result(), expected)

    def test_result_key_is_missing(self):
        self.method.side_effect = [
            {'not_a_result_key': 'this page will be ignored', 'Marker': '_'},
            {'neither_this_one': 'this page will be ignored, too'},
        ]
        pages = self.paginator.paginate()
        expected = {}
        self.assertEqual(pages.build_full_result(), expected)


class TestIncludeNonResultKeys(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.method = mock.Mock()
        self.model = mock.Mock()
        self.paginate_config = {
            'output_token': 'NextToken',
            'input_token': 'NextToken',
            'result_key': 'ResultKey',
            'non_aggregate_keys': ['NotResultKey'],
        }
        self.paginator = Paginator(self.method, self.paginate_config, self.model)

    def test_include_non_aggregate_keys(self):
        self.method.side_effect = [
            {'ResultKey': ['foo'], 'NotResultKey': 'a', 'NextToken': 't1'},
            {'ResultKey': ['bar'], 'NotResultKey': 'a', 'NextToken': 't2'},
            {'ResultKey': ['baz'], 'NotResultKey': 'a'},
        ]
        pages = self.paginator.paginate()
        actual = pages.build_full_result()
        self.assertEqual(pages.non_aggregate_part, {'NotResultKey': 'a'})
        expected = {
            'ResultKey': ['foo', 'bar', 'baz'],
            'NotResultKey': 'a',
        }
        self.assertEqual(actual, expected)

    def test_include_with_multiple_result_keys(self):
        self.paginate_config['result_key'] = ['ResultKey1', 'ResultKey2']
        self.paginator = Paginator(self.method, self.paginate_config, self.model)
        self.method.side_effect = [
            {'ResultKey1': ['a', 'b'], 'ResultKey2': ['u', 'v'],
             'NotResultKey': 'a', 'NextToken': 'token1'},
            {'ResultKey1': ['c', 'd'], 'ResultKey2': ['w', 'x'],
             'NotResultKey': 'a', 'NextToken': 'token2'},
            {'ResultKey1': ['e', 'f'], 'ResultKey2': ['y', 'z'],
             'NotResultKey': 'a'}
        ]
        pages = self.paginator.paginate()
        actual = pages.build_full_result()
        expected = {
            'ResultKey1': ['a', 'b', 'c', 'd', 'e', 'f'],
            'ResultKey2': ['u', 'v', 'w', 'x', 'y', 'z'],
            'NotResultKey': 'a',
        }
        self.assertEqual(actual, expected)

    def test_include_with_nested_result_keys(self):
        self.paginate_config['result_key'] = 'Result.Key'
        self.paginate_config['non_aggregate_keys'] = [
            'Outer', 'Result.Inner',
        ]
        self.paginator = Paginator(self.method, self.paginate_config, self.model)
        self.method.side_effect = [
            # The non result keys shows hypothetical
            # example.  This doesn't actually happen,
            # but in the case where the non result keys
            # are different across pages, we use the values
            # from the first page.
            {'Result': {'Key': ['foo'], 'Inner': 'v1'},
             'Outer': 'v2', 'NextToken': 't1'},
            {'Result': {'Key': ['bar', 'baz'], 'Inner': 'v3'},
             'Outer': 'v4', 'NextToken': 't2'},
            {'Result': {'Key': ['qux'], 'Inner': 'v5'},
             'Outer': 'v6'},
        ]
        pages = self.paginator.paginate()
        actual = pages.build_full_result()
        self.assertEqual(pages.non_aggregate_part,
                         {'Outer': 'v2', 'Result': {'Inner': 'v1'}})
        expected = {
            'Result': {'Key': ['foo', 'bar', 'baz', 'qux'], 'Inner': 'v1'},
            'Outer': 'v2',
        }
        self.assertEqual(actual, expected)


class TestSearchOverResults(unittest.TestCase):
    def setUp(self):
        self.method = mock.Mock()
        self.model = mock.Mock()
        self.paginate_config = {
            'more_results': 'IsTruncated',
            'output_token': 'NextToken',
            'input_token': 'NextToken',
            'result_key': 'Foo',
        }
        self.paginator = Paginator(self.method, self.paginate_config, self.model)
        responses = [
            {'Foo': [{'a': 1}, {'b': 2}],
             'IsTruncated': True, 'NextToken': '1'},
            {'Foo': [{'a': 3}, {'b': 4}],
             'IsTruncated': True, 'NextToken': '2'},
            {'Foo': [{'a': 5}], 'IsTruncated': False, 'NextToken': '3'}
        ]
        self.method.side_effect = responses

    def test_yields_non_list_values(self):
        result = list(self.paginator.paginate().search('Foo[0].a'))
        self.assertEqual([1, 3, 5], result)

    def test_yields_individual_list_values(self):
        result = list(self.paginator.paginate().search('Foo[].*[]'))
        self.assertEqual([1, 2, 3, 4, 5], result)

    def test_empty_when_no_match(self):
        result = list(self.paginator.paginate().search('Foo[].qux'))
        self.assertEqual([], result)

    def test_no_yield_when_no_match_on_page(self):
        result = list(self.paginator.paginate().search('Foo[].b'))
        self.assertEqual([2, 4], result)


class TestDeprecatedStartingToken(unittest.TestCase):
    def setUp(self):
        self.method = mock.Mock()
        self.model = mock.Mock()

    def create_paginator(self, multiple_tokens=False):
        if multiple_tokens:
            paginator_config = {
                "output_token": ["Marker1", "Marker2"],
                "input_token": ["InMarker1", "InMarker2"],
                "result_key": ["Users", "Groups"],
            }
        else:
            paginator_config = {
                'output_token': 'Marker',
                'input_token': 'Marker',
                'result_key': 'Users',
            }
        return Paginator(self.method, paginator_config, self.model)

    def assert_pagination_result(self, expected, pagination_config,
                                 multiple_tokens=False):
        paginator = self.create_paginator(multiple_tokens)
        try:
            actual = paginator.paginate(
                PaginationConfig=pagination_config).build_full_result()
            self.assertEqual(actual, expected)
        except ValueError:
            self.fail("Deprecated paginator failed.")

    def test_deprecated_starting_token(self):
        responses = [
            {"Users": ["User1"], "Marker": "m2"},
            {"Users": ["User2"], "Marker": "m3"},
            {"Users": ["User3"]},
        ]
        self.method.side_effect = responses
        pagination_config = {'StartingToken': 'm1___0'}
        expected = {'Users': ['User1', 'User2', 'User3']}
        self.assert_pagination_result(expected, pagination_config)

    def test_deprecated_multiple_starting_token(self):
        responses = [
            {
                "Users": ["User1", "User2"],
                "Groups": ["Group1"],
                "Marker1": "m1",
                "Marker2": "m2"
            },
            {
                "Users": ["User3", "User4"],
                "Groups": ["Group2"],
                "Marker1": "m3",
                "Marker2": "m4"
            },
            {
                "Users": ["User5"],
                "Groups": ["Group3"]
            }
        ]
        self.method.side_effect = responses
        pagination_config = {'StartingToken': 'm0___m0___1'}
        expected = {
            'Groups': ['Group2', 'Group3'],
            'Users': ['User2', 'User3', 'User4', 'User5']
        }
        self.assert_pagination_result(
            expected, pagination_config, multiple_tokens=True)

    def test_deprecated_starting_token_returns_new_style_next_token(self):
        responses = [
            {"Users": ["User1"], "Marker": "m2"},
            {"Users": ["User2"], "Marker": "m3"},
            {"Users": ["User3"], "Marker": "m4"},
        ]
        self.method.side_effect = responses
        pagination_config = {'StartingToken': 'm1___0', 'MaxItems': 3}
        expected = {
            'Users': ['User1', 'User2', 'User3'],
            'NextToken': encode_token({'Marker': 'm4'})
        }
        self.assert_pagination_result(expected, pagination_config)

    def test_deprecated_starting_token_without_all_input_set_to_none(self):
        responses = [
            {
                "Users": ["User1", "User2"],
                "Groups": ["Group1"],
                "Marker1": "m1",
                "Marker2": "m2"
            },
            {
                "Users": ["User3", "User4"],
                "Groups": ["Group2"],
                "Marker1": "m3",
                "Marker2": "m4"
            },
            {
                "Users": ["User5"],
                "Groups": ["Group3"]
            }
        ]
        self.method.side_effect = responses
        pagination_config = {'StartingToken': 'm0'}
        expected = {
            'Groups': ['Group2', 'Group3'],
            'Users': ['User1', 'User2', 'User3', 'User4', 'User5']
        }
        self.assert_pagination_result(
            expected, pagination_config, multiple_tokens=True)

    def test_deprecated_starting_token_rejects_too_many_input_tokens(self):
        responses = [
            {"Users": ["User1"], "Marker": "m2"},
            {"Users": ["User2"], "Marker": "m3"},
            {"Users": ["User3"]},
        ]
        self.method.side_effect = responses
        pagination_config = {'StartingToken': 'm1___m4___0'}
        expected = {'Users': ['User1', 'User2', 'User3']}

        paginator = self.create_paginator()
        with self.assertRaises(ValueError):
            actual = paginator.paginate(
                PaginationConfig=pagination_config).build_full_result()
            self.assertEqual(actual, expected)


class TestStringPageSize(unittest.TestCase):
    def setUp(self):
        self.service_model = {
            'metadata': {
                'protocol': 'query',
                'endpointPrefix': 'prefix'
            },
            'documentation': 'best service ever',
            'operations': {
                'ListStuff': {
                    'name': 'ListStuff',
                    'http': {
                        'method': 'GET',
                        'requestUri': '/things'
                    },
                    'input': {'shape': 'ListStuffInputShape'},
                    'output': {'shape': 'ListStuffOutputShape'},
                    'errors': [],
                    'documentation': 'Lists stuff'
                }
            },
            'shapes': {
                'String': {'type': 'string'},
                'ListOfStuff': {
                    'type': 'list',
                    'member': {'type': 'string'}
                },
                'ListStuffInputShape': {
                    'type': 'structure',
                    'required': [],
                    'members': {
                        'NextToken': {'shape': 'String'},
                        'MaxItems': {'shape': 'String'}
                    }
                },
                'ListStuffOutputShape': {
                    'type': 'structure',
                    'required': [],
                    'members': {
                        'NextToken': {'shape': 'String'},
                        'Stuff': {'shape': 'ListOfStuff'},
                        'IsTruncated': {'type': 'boolean'}
                    },
                }
            }
        }
        self.paginate_config = {
            'input_token': 'NextToken',
            'output_token': 'NextToken',
            'limit_key': 'MaxItems',
            'result_key': 'Stuff',
        }
        self.service = model.ServiceModel(self.service_model)
        self.model = self.service.operation_model('ListStuff')
        self.method = mock.Mock()
        self.method.side_effect = [{}]
        self.paginator = Paginator(self.method, self.paginate_config, self.model)

    def test_int_page_size(self):
        res = list(self.paginator.paginate(PaginationConfig={'PageSize': 1}))
        self.method.assert_called_with(MaxItems='1')

    def test_str_page_size(self):
        res = list(self.paginator.paginate(PaginationConfig={'PageSize': '1'}))
        self.method.assert_called_with(MaxItems='1')


if __name__ == '__main__':
    unittest.main()
