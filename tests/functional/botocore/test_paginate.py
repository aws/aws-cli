# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from math import ceil
from datetime import datetime

import pytest

from tests import random_chars
from tests import BaseSessionTest
from botocore.stub import Stubber, StubAssertionError
from botocore.paginate import TokenDecoder, TokenEncoder
from botocore.compat import six


class TestRDSPagination(BaseSessionTest):
    def setUp(self):
        super(TestRDSPagination, self).setUp()
        self.region = 'us-west-2'
        self.client = self.session.create_client(
            'rds', self.region)
        self.stubber = Stubber(self.client)

    def test_can_specify_zero_marker(self):
        service_response = {
            'LogFileData': 'foo',
            'Marker': '2',
            'AdditionalDataPending': True
        }
        expected_params = {
            'DBInstanceIdentifier': 'foo',
            'LogFileName': 'bar',
            'NumberOfLines': 2,
            'Marker': '0'
        }
        function_name = 'download_db_log_file_portion'

        # The stubber will assert that the function is called with the expected
        # parameters.
        self.stubber.add_response(
            function_name, service_response, expected_params)
        self.stubber.activate()

        try:
            paginator = self.client.get_paginator(function_name)
            result = paginator.paginate(
                DBInstanceIdentifier='foo',
                LogFileName='bar',
                NumberOfLines=2,
                PaginationConfig={
                    'StartingToken': '0',
                    'MaxItems': 3
                }).build_full_result()
            self.assertEqual(result['LogFileData'], 'foo')
            self.assertIn('NextToken', result)
        except StubAssertionError as e:
            self.fail(str(e))


class TestAutoscalingPagination(BaseSessionTest):
    def setUp(self):
        super(TestAutoscalingPagination, self).setUp()
        self.region = 'us-west-2'
        self.client = self.session.create_client(
            'autoscaling', self.region, aws_secret_access_key='foo',
            aws_access_key_id='bar', aws_session_token='baz'
        )
        self.stubber = Stubber(self.client)
        self.stubber.activate()

    def _setup_scaling_pagination(self, page_size=200, max_items=100,
                                 total_items=600):
        """
        Add to the stubber to test paginating describe_scaling_activities.

        WARNING: This only handles cases where max_items cleanly divides
        page_size.
        """
        requests_per_page = page_size / max_items
        if requests_per_page != ceil(requests_per_page):
            raise NotImplementedError(
                "This only handles setup where max_items is less than "
                "page_size and where max_items evenly divides page_size."
            )
        requests_per_page = int(requests_per_page)
        num_pages = int(ceil(total_items / page_size))

        previous_next_token = None
        for i in range(num_pages):
            page = self.create_describe_scaling_response(page_size=page_size)

            # Don't create a next_token for the final page
            if i + 1 == num_pages:
                next_token = None
            else:
                next_token = random_chars(10)

            expected_args = {}
            if previous_next_token:
                expected_args['StartingToken'] = previous_next_token

            # The same page may be accessed multiple times because we are
            # truncating it at max_items
            for _ in range(requests_per_page - 1):
                # The page is copied because the paginator will modify the
                # response object, causing issues when using the stubber.
                self.stubber.add_response(
                    'describe_scaling_activities', page.copy()
                )

            if next_token is not None:
                page['NextToken'] = next_token

            # Copying the page here isn't necessary because it is about to
            # be blown away anyway.
            self.stubber.add_response(
                'describe_scaling_activities', page
            )

            previous_next_token = next_token

    def create_describe_scaling_response(self, page_size=200):
        """Create a valid describe_scaling_activities response."""
        page = []
        date = datetime.now()
        for _ in range(page_size):
            page.append({
                'AutoScalingGroupName': 'test',
                'ActivityId': random_chars(10),
                'Cause': 'test',
                'StartTime': date,
                'StatusCode': '200',
            })
        return {'Activities': page}

    def test_repeated_build_full_results(self):
        # This ensures that we can cleanly paginate using build_full_results.
        max_items = 100
        total_items = 600
        self._setup_scaling_pagination(
            max_items=max_items,
            total_items=total_items,
            page_size=200
        )
        paginator = self.client.get_paginator('describe_scaling_activities')
        conf = {'MaxItems': max_items}

        pagination_tokens = []

        result = paginator.paginate(PaginationConfig=conf).build_full_result()
        all_results = result['Activities']
        while 'NextToken' in result:
            starting_token = result['NextToken']
            # We should never get a duplicate pagination token.
            self.assertNotIn(starting_token, pagination_tokens)
            pagination_tokens.append(starting_token)

            conf['StartingToken'] = starting_token
            pages = paginator.paginate(PaginationConfig=conf)
            result = pages.build_full_result()
            all_results.extend(result['Activities'])

        self.assertEqual(len(all_results), total_items)


class TestCloudwatchLogsPagination(BaseSessionTest):
    def setUp(self):
        super(TestCloudwatchLogsPagination, self).setUp()
        self.region = 'us-west-2'
        self.client = self.session.create_client(
            'logs', self.region, aws_secret_access_key='foo',
            aws_access_key_id='bar', aws_session_token='baz'
        )
        self.stubber = Stubber(self.client)
        self.stubber.activate()

    def test_token_with_triple_underscores(self):
        response = {
            'events': [{
                'logStreamName': 'foobar',
                'timestamp': 1560195817,
                'message': 'a thing happened',
                'ingestionTime': 1560195817,
                'eventId': 'foo',
            }],
            'searchedLogStreams': [{
                'logStreamName': 'foobar',
                'searchedCompletely': False,
            }],
        }
        group_name = 'foo'
        token = 'foo___bar'
        expected_args = {
            'logGroupName': group_name,
            'nextToken': token,
        }
        self.stubber.add_response('filter_log_events', response, expected_args)
        paginator = self.client.get_paginator('filter_log_events')
        pages = paginator.paginate(
            PaginationConfig={
                'MaxItems': 1,
                'StartingToken': token,
            },
            logGroupName=group_name,
        )
        result = pages.build_full_result()
        self.assertEqual(len(result['events']), 1)


@pytest.mark.parametrize(
    "token_dict",
    (
        {'foo': 'bar'},
        {'foo': b'bar'},
        {'foo': {'bar': b'baz'}},
        {'foo': ['bar', b'baz']},
        {'foo': b'\xff'},
        {'foo': {'bar': b'baz', 'bin': [b'bam']}},
    )
)
def test_token_encoding(token_dict):
    encoded = TokenEncoder().encode(token_dict)
    assert isinstance(encoded, six.string_types)
    decoded = TokenDecoder().decode(encoded)
    assert decoded == token_dict
