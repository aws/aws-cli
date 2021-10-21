# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import logging
import datetime
from tests import unittest, random_chars

import botocore.session
from botocore.client import ClientError
from botocore.compat import six
from botocore.exceptions import EndpointConnectionError


# This is really a combination of testing the debug logging mechanism
# as well as the response wire log, which theoretically could be
# implemented in any number of modules, which makes it hard to pick
# which integration test module this code should live in, so I picked
# the client module.
class TestResponseLog(unittest.TestCase):

    def test_debug_log_contains_headers_and_body(self):
        # This test just verifies that the response headers/body
        # are in the debug log.  It's an integration test so that
        # we can refactor the code however we want, as long as we don't
        # lose this feature.
        session = botocore.session.get_session()
        client = session.create_client('s3', region_name='us-west-2')
        debug_log = six.StringIO()
        session.set_stream_logger('', logging.DEBUG, debug_log)
        client.list_buckets()
        debug_log_contents = debug_log.getvalue()
        self.assertIn('Response headers', debug_log_contents)
        self.assertIn('Response body', debug_log_contents)


class TestAcceptedDateTimeFormats(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()
        self.client = self.session.create_client('emr', 'us-west-2')

    def test_accepts_datetime_object(self):
        response = self.client.list_clusters(
            CreatedAfter=datetime.datetime.now())
        self.assertIn('Clusters', response)

    def test_accepts_epoch_format(self):
        response = self.client.list_clusters(CreatedAfter=0)
        self.assertIn('Clusters', response)

    def test_accepts_iso_8601_unaware(self):
        response = self.client.list_clusters(
            CreatedAfter='2014-01-01T00:00:00')
        self.assertIn('Clusters', response)

    def test_accepts_iso_8601_utc(self):
        response = self.client.list_clusters(
            CreatedAfter='2014-01-01T00:00:00Z')
        self.assertIn('Clusters', response)

    def test_accepts_iso_8701_local(self):
        response = self.client.list_clusters(
            CreatedAfter='2014-01-01T00:00:00-08:00')
        self.assertIn('Clusters', response)


class TestClientErrors(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()

    def test_region_mentioned_in_invalid_region(self):
        client = self.session.create_client(
            'cloudformation', region_name='us-east-999')
        with self.assertRaisesRegex(EndpointConnectionError,
                                    'Could not connect to the endpoint URL'):
            client.list_stacks()

    def test_client_modeled_exception(self):
        client = self.session.create_client(
            'dynamodb', region_name='us-west-2')
        with self.assertRaises(client.exceptions.ResourceNotFoundException):
            client.describe_table(TableName="NonexistentTable")

    def test_client_modeleded_exception_with_differing_code(self):
        client = self.session.create_client('iam', region_name='us-west-2')
        # The NoSuchEntityException should be raised on NoSuchEntity error
        # code.
        with self.assertRaises(client.exceptions.NoSuchEntityException):
            client.get_role(RoleName="NonexistentIAMRole")

    def test_raises_general_client_error_for_non_modeled_exception(self):
        client = self.session.create_client('ec2', region_name='us-west-2')
        try:
            client.describe_regions(DryRun=True)
        except client.exceptions.ClientError as e:
            self.assertIs(e.__class__, ClientError)

    def test_can_catch_client_exceptions_across_two_different_clients(self):
        client = self.session.create_client(
            'dynamodb', region_name='us-west-2')
        client2 = self.session.create_client(
            'dynamodb', region_name='us-west-2')
        with self.assertRaises(client2.exceptions.ResourceNotFoundException):
            client.describe_table(TableName="NonexistentTable")


class TestClientMeta(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()

    def test_region_name_on_meta(self):
        client = self.session.create_client('s3', 'us-west-2')
        self.assertEqual(client.meta.region_name, 'us-west-2')

    def test_endpoint_url_on_meta(self):
        client = self.session.create_client('s3', 'us-west-2',
                                            endpoint_url='https://foo')
        self.assertEqual(client.meta.endpoint_url, 'https://foo')


class TestClientInjection(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()

    def test_can_inject_client_methods(self):

        def extra_client_method(self, name):
            return name

        def inject_client_method(class_attributes, **kwargs):
            class_attributes['extra_client_method'] = extra_client_method

        self.session.register('creating-client-class.s3',
                              inject_client_method)

        client = self.session.create_client('s3', 'us-west-2')

        # We should now have access to the extra_client_method above.
        self.assertEqual(client.extra_client_method('foo'), 'foo')


class TestMixedEndpointCasing(unittest.TestCase):
    def setUp(self):
        self.url = 'https://EC2.US-WEST-2.amazonaws.com/'
        self.session = botocore.session.get_session()
        self.client = self.session.create_client('ec2', 'us-west-2',
                                                 endpoint_url=self.url)

    def test_sigv4_is_correct_when_mixed_endpoint_casing(self):
        res = self.client.describe_regions()
        status_code = res['ResponseMetadata']['HTTPStatusCode']
        self.assertEqual(status_code, 200)
