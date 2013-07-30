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
            'output_token': 'NextToken',
            'py_input_token': 'NextToken',
            'result_key': 'Foo',
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

    def test_next_token_with_or_expression(self):
        self.operation.pagination = {
            'output_token': 'NextToken or NextToken2',
            'py_input_token': 'NextToken',
            'result_key': 'Foo',
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
            'more_key': 'IsTruncated',
            'output_token': 'NextToken',
            'py_input_token': 'NextToken',
            'result_key': 'Foo',
        }
        self.operation.pagination = self.paginate_config
        self.paginator = Paginator(self.operation)
        responses = [
            (None, {'Foo': [1], 'IsTruncated': True, 'NextToken': 'token1'}),
            (None, {'Foo': [2], 'IsTruncated': True, 'NextToken': 'token2'}),
            (None, {'Foo': [3], 'IsTruncated': False, 'NextToken': 'token3'}),
            (None, {'Foo': [4], 'not_next_token': 'foo'}),
        ]
        self.operation.call.side_effect = responses
        list(self.paginator.paginate(None))
        self.assertEqual(
            self.operation.call.call_args_list,
            [mock.call(None),
             mock.call(None, NextToken='token1'),
             mock.call(None, NextToken='token2'),])

    def test_more_tokens_is_path_expression(self):
        self.paginate_config = {
            'more_key': 'Foo.IsTruncated',
            'output_token': 'NextToken',
            'py_input_token': 'NextToken',
            'result_key': 'Bar',
        }
        self.operation.pagination = self.paginate_config
        self.paginator = Paginator(self.operation)
        responses = [
            (None, {'Foo': {'IsTruncated': True}, 'NextToken': 'token1'}),
            (None, {'Foo': {'IsTruncated': False}, 'NextToken': 'token2'}),
        ]
        self.operation.call.side_effect = responses
        list(self.paginator.paginate(None))
        self.assertEqual(
            self.operation.call.call_args_list,
            [mock.call(None),
             mock.call(None, NextToken='token1'),])


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
            'output_token': [
                'NextMarker or ListBucketResult.Contents[-1].Key'],
            'py_input_token': 'next_marker',
            'result_key': 'Contents',
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


class TestMultipleTokens(unittest.TestCase):
    def setUp(self):
        self.operation = mock.Mock()
        # This is something we'd see in s3 pagination.
        self.paginate_config = {
            "output_token": ["ListBucketResults.NextKeyMarker",
                             "ListBucketResults.NextUploadIdMarker"],
            "py_input_token": ["key_marker", "upload_id_marker"],
            "result_key": 'Foo',
        }
        self.operation.pagination = self.paginate_config
        self.paginator = Paginator(self.operation)

    def test_s3_list_multipart_uploads(self):
        responses = [
            (None, {"Foo": [1], "ListBucketResults": {"NextKeyMarker": "key1",
                    "NextUploadIdMarker": "up1"}}),
            (None, {"Foo": [2], "ListBucketResults": {"NextKeyMarker": "key2",
                    "NextUploadIdMarker": "up2"}}),
            (None, {"Foo": [3], "ListBucketResults": {"NextKeyMarker": "key3",
                    "NextUploadIdMarker": "up3"}}),
            (None, {}),
        ]
        self.operation.call.side_effect = responses
        list(self.paginator.paginate(None))
        self.assertEqual(
            self.operation.call.call_args_list,
            [mock.call(None),
             mock.call(None, key_marker='key1', upload_id_marker='up1'),
             mock.call(None, key_marker='key2', upload_id_marker='up2'),
             mock.call(None, key_marker='key3', upload_id_marker='up3'),
             ])


class TestKeyIterators(unittest.TestCase):
    def setUp(self):
         self.operation = mock.Mock()
         # This is something we'd see in s3 pagination.
         self.paginate_config = {
             "output_token": "Marker",
             "py_input_token": "Marker",
             "result_key": "Users"
         }
         self.operation.pagination = self.paginate_config
         self.paginator = Paginator(self.operation)

    def test_result_key_iters(self):
        responses = [
            (None, {"Users": ["User1"], "Marker": "m1"}),
            (None, {"Users": ["User2"], "Marker": "m2"}),
            (None, {"Users": ["User3"]}),
        ]
        self.operation.call.side_effect = responses
        pages = self.paginator.paginate(None)
        iterators = pages.result_key_iters()
        self.assertEqual(len(iterators), 1)
        self.assertEqual(list(iterators[0]),
                         ["User1", "User2", "User3"])
        self.assertEqual(len(pages.http_responses), 3)

    def test_build_full_result_with_single_key(self):
        responses = [
            (None, {"Users": ["User1"], "Marker": "m1"}),
            (None, {"Users": ["User2"], "Marker": "m2"}),
            (None, {"Users": ["User3"]}),
        ]
        self.operation.call.side_effect = responses
        pages = self.paginator.paginate(None)
        complete = pages.build_full_result()
        self.assertEqual(complete, {'Users': ['User1', 'User2', 'User3']})

    def test_max_items_can_be_specified(self):
        paginator = Paginator(self.operation)
        responses = [
            (None, {"Users": ["User1"], "Marker": "m1"}),
            (None, {"Users": ["User2"], "Marker": "m2"}),
            (None, {"Users": ["User3"]}),
        ]
        self.operation.call.side_effect = responses
        self.assertEqual(
            paginator.paginate(None, max_items=1).build_full_result(),
            {'Users': ['User1'], 'NextToken': 'm1'})

    def test_next_token_on_page_boundary(self):
        paginator = Paginator(self.operation)
        responses = [
            (None, {"Users": ["User1"], "Marker": "m1"}),
            (None, {"Users": ["User2"], "Marker": "m2"}),
            (None, {"Users": ["User3"]}),
        ]
        self.operation.call.side_effect = responses
        self.assertEqual(
            paginator.paginate(None, max_items=2).build_full_result(),
            {'Users': ['User1', 'User2'], 'NextToken': 'm2'})

    def test_max_items_can_be_specified_truncates_response(self):
        # We're saying we only want 4 items, but notice that the second
        # page of results returns users 4-6 so we have to truncated
        # part of that second page.
        paginator = Paginator(self.operation)
        responses = [
            (None, {"Users": ["User1", "User2", "User3"], "Marker": "m1"}),
            (None, {"Users": ["User4", "User5", "User6"], "Marker": "m2"}),
            (None, {"Users": ["User7"]}),
        ]
        self.operation.call.side_effect = responses
        self.assertEqual(
            paginator.paginate(None, max_items=4).build_full_result(),
            {'Users': ['User1', 'User2', 'User3', 'User4'],
             'NextToken': 'm1___1'})

    def test_resume_next_marker_mid_page(self):
        # This is a simulation of picking up from the response
        # from test_max_items_can_be_specified_truncates_response
        # We got the first 4 users, when we pick up we should get
        # User5 - User7.
        paginator = Paginator(self.operation)
        responses = [
            (None, {"Users": ["User4", "User5", "User6"], "Marker": "m2"}),
            (None, {"Users": ["User7"]}),
        ]
        self.operation.call.side_effect = responses
        self.assertEqual(
            paginator.paginate(None, starting_token='m1___1').build_full_result(),
            {'Users': ['User5', 'User6', 'User7']})
        self.assertEqual(
            self.operation.call.call_args_list,
            [mock.call(None, Marker='m1'),
             mock.call(None, Marker='m2'),])

    def test_max_items_exceeds_actual_amount(self):
        # Because MaxItems=10 > number of users (3), we should just return
        # all of the users.
        paginator = Paginator(self.operation)
        responses = [
            (None, {"Users": ["User1"], "Marker": "m1"}),
            (None, {"Users": ["User2"], "Marker": "m2"}),
            (None, {"Users": ["User3"]}),
        ]
        self.operation.call.side_effect = responses
        self.assertEqual(
            paginator.paginate(None, max_items=10).build_full_result(),
            {'Users': ['User1', 'User2', 'User3']})

    def test_bad_input_tokens(self):
        responses = [
            (None, {"Users": ["User1"], "Marker": "m1"}),
            (None, {"Users": ["User2"], "Marker": "m2"}),
            (None, {"Users": ["User3"]}),
        ]
        self.operation.call.side_effect = responses
        with self.assertRaisesRegexp(ValueError, 'Bad starting token'):
            self.paginator.paginate(
                None, starting_token='bad___notanint').build_full_result()


class TestMultipleResultKeys(unittest.TestCase):
    def setUp(self):
        self.operation = mock.Mock()
        # This is something we'd see in s3 pagination.
        self.paginate_config = {
            "output_token": "Marker",
            "py_input_token": "Marker",
            "result_key": ["Users", "Groups"],
        }
        self.operation.pagination = self.paginate_config
        self.paginator = Paginator(self.operation)

    def test_build_full_result_with_multiple_result_keys(self):
        responses = [
            (None, {"Users": ["User1"], "Groups": ["Group1"], "Marker": "m1"}),
            (None, {"Users": ["User2"], "Groups": ["Group2"], "Marker": "m2"}),
            (None, {"Users": ["User3"], "Groups": ["Group3"], }),
        ]
        self.operation.call.side_effect = responses
        pages = self.paginator.paginate(None)
        complete = pages.build_full_result()
        self.assertEqual(complete,
                         {"Users": ['User1', 'User2', 'User3'],
                          "Groups": ['Group1', 'Group2', 'Group3']})

    def test_build_full_result_with_different_length_result_keys(self):
        responses = [
            (None, {"Users": ["User1"], "Groups": ["Group1"], "Marker": "m1"}),
            # Then we stop getting "Users" output, but we get more "Groups"
            (None, {"Users": [], "Groups": ["Group2"], "Marker": "m2"}),
            (None, {"Users": [], "Groups": ["Group3"], }),
        ]
        self.operation.call.side_effect = responses
        pages = self.paginator.paginate(None)
        complete = pages.build_full_result()
        self.assertEqual(complete,
                         {"Users": ['User1'],
                          "Groups": ['Group1', 'Group2', 'Group3']})

    def test_build_full_result_with_zero_length_result_key(self):
        responses = [
            # In this case the 'Users' key is always empty but we should
            # have a 'Users' key in the output, it should just have an
            # empty list for a value.
            (None, {"Users": [], "Groups": ["Group1"], "Marker": "m1"}),
            (None, {"Users": [], "Groups": ["Group2"], "Marker": "m2"}),
            (None, {"Users": [], "Groups": ["Group3"], }),
        ]
        self.operation.call.side_effect = responses
        pages = self.paginator.paginate(None)
        complete = pages.build_full_result()
        self.assertEqual(complete,
                         {"Users": [],
                          "Groups": ['Group1', 'Group2', 'Group3']})

    def test_build_result_with_secondary_keys(self):
        responses = [
            (None, {"Users": ["User1", "User2"],
                    "Groups": ["Group1", "Group2"],
                    "Marker": "m1"}),
            (None, {"Users": ["User3"], "Groups": ["Group3"], "Marker": "m2"}),
            (None, {"Users": ["User4"], "Groups": ["Group4"], }),
        ]
        self.operation.call.side_effect = responses
        pages = self.paginator.paginate(None, max_items=1)
        complete = pages.build_full_result()
        self.assertEqual(complete,
                         {"Users": ["User1"], "Groups": ["Group1", "Group2"],
                          "NextToken": "None___1"})

    def test_resume_with_secondary_keys(self):
        # This is simulating a continutation of the previous test,
        # test_build_result_with_secondary_keys.  We use the
        # token specified in the response "None___1" to continue where we
        # left off.
        responses = [
            (None, {"Users": ["User1", "User2"],
                    "Groups": ["Group1", "Group2"],
                    "Marker": "m1"}),
            (None, {"Users": ["User3"], "Groups": ["Group3"], "Marker": "m2"}),
            (None, {"Users": ["User4"], "Groups": ["Group4"], }),
        ]
        self.operation.call.side_effect = responses
        pages = self.paginator.paginate(None, max_items=1,
                                        starting_token="None___1")
        complete = pages.build_full_result()
        # Note that the secondary keys ("Groups") are all truncated because
        # they were in the original (first) response.
        self.assertEqual(complete,
                         {"Users": ["User2"], "Groups": [],
                          "NextToken": "m1"})


class TestMultipleInputKeys(unittest.TestCase):
    def setUp(self):
        self.operation = mock.Mock()
        # Probably the most complicated example we'll see:
        # multiple input/output/result keys.
        self.paginate_config = {
            "output_token": ["Marker1", "Marker2"],
            "py_input_token": ["InMarker1", "InMarker2"],
            "result_key": ["Users", "Groups"],
        }
        self.operation.pagination = self.paginate_config
        self.paginator = Paginator(self.operation)

    def test_build_full_result_with_multiple_input_keys(self):
        responses = [
            (None, {"Users": ["User1", "User2"], "Groups": ["Group1"],
                    "Marker1": "m1", "Marker2": "m2"}),
            (None, {"Users": ["User3", "User4"], "Groups": ["Group2"],
                    "Marker1": "m3", "Marker2": "m4"}),
            (None, {"Users": ["User5"], "Groups": ["Group3"], }),
        ]
        self.operation.call.side_effect = responses
        pages = self.paginator.paginate(None, max_items=3)
        complete = pages.build_full_result()
        self.assertEqual(complete,
                         {"Users": ['User1', 'User2', 'User3'],
                          "Groups": ['Group1', 'Group2'],
                          "NextToken": "m1___m2___1"})

    def test_resume_with_multiple_input_keys(self):
        responses = [
            (None, {"Users": ["User3", "User4"], "Groups": ["Group2"],
                    "Marker1": "m3", "Marker2": "m4"}),
            (None, {"Users": ["User5"], "Groups": ["Group3"], }),
        ]
        self.operation.call.side_effect = responses
        pages = self.paginator.paginate(None, max_items=1,
                                        starting_token='m1___m2___1')
        complete = pages.build_full_result()
        self.assertEqual(complete,
                         {"Users": ['User4'],
                          "Groups": [],
                          "NextToken": "m3___m4"})
        self.assertEqual(
            self.operation.call.call_args_list,
            [mock.call(None, InMarker1='m1', InMarker2='m2'),])


if __name__ == '__main__':
    unittest.main()
