# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import mock
from botocore.exceptions import ClientError

from awscli.testutils import unittest
from awscli.compat import StringIO
from awscli.customizations.configservice.subscribe import SubscribeCommand, \
    S3BucketHelper, SNSTopicHelper


class TestS3BucketHelper(unittest.TestCase):
    def setUp(self):
        self.s3_client = mock.Mock()
        self.helper = S3BucketHelper(self.s3_client)
        self.error_response = {
            'Error': {
                'Code': '404',
                'Message': 'Not Found'
            }
        }
        self.bucket_no_exists_error = ClientError(
            self.error_response,
            'HeadBucket'
        )

    def test_correct_prefix_returned(self):
        name = 'MyBucket/MyPrefix'
        bucket, prefix = self.helper.prepare_bucket(name)
        # Ensure the returned bucket and key are as expected
        self.assertEqual(bucket, 'MyBucket')
        self.assertEqual(prefix, 'MyPrefix')

    def test_bucket_exists(self):
        name = 'MyBucket'
        bucket, prefix = self.helper.prepare_bucket(name)
        # A new bucket should not have been created because no error was thrown
        self.assertFalse(self.s3_client.create_bucket.called)
        # Ensure the returned bucket and key are as expected
        self.assertEqual(bucket, name)
        self.assertEqual(prefix, '')

    def test_bucket_no_exist(self):
        name = 'MyBucket/MyPrefix'
        self.s3_client.head_bucket.side_effect = self.bucket_no_exists_error
        self.s3_client._endpoint.region_name = 'us-east-1'
        bucket, prefix = self.helper.prepare_bucket(name)
        # Ensure that the create bucket was called with the proper args.
        self.s3_client.create_bucket.assert_called_with(
            Bucket='MyBucket'
        )
        # Ensure the returned bucket and key are as expected
        self.assertEqual(bucket, 'MyBucket')
        self.assertEqual(prefix, 'MyPrefix')

    def test_bucket_no_exist_with_location_constraint(self):
        name = 'MyBucket/MyPrefix'
        self.s3_client.head_bucket.side_effect = self.bucket_no_exists_error
        self.s3_client._endpoint.region_name = 'us-west-2'
        bucket, prefix = self.helper.prepare_bucket(name)
        # Ensure that the create bucket was called with the proper args.
        self.s3_client.create_bucket.assert_called_with(
            Bucket='MyBucket',
            CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
        )
        # Ensure the returned bucket and key are as expected
        self.assertEqual(bucket, 'MyBucket')
        self.assertEqual(prefix, 'MyPrefix')

    def test_bucket_client_exception_non_404(self):
        name = 'MyBucket/MyPrefix'
        self.error_response['Error']['Code'] = '403'
        self.error_response['Error']['Message'] = 'Forbidden'
        forbidden_error = ClientError(self.error_response, 'HeadBucket')
        self.s3_client.head_bucket.side_effect = forbidden_error
        self.s3_client._endpoint.region_name = 'us-east-1'
        bucket, prefix = self.helper.prepare_bucket(name)
        # A new bucket should not have been created because a 404 error
        # was not thrown
        self.assertFalse(self.s3_client.create_bucket.called)
        # Ensure the returned bucket and key are as expected
        self.assertEqual(bucket, 'MyBucket')
        self.assertEqual(prefix, 'MyPrefix')

    def test_output_use_existing_bucket(self):
        name = 'MyBucket/MyPrefix'
        with mock.patch('sys.stdout', StringIO()) as mock_stdout:
            self.helper.prepare_bucket(name)
            self.assertIn(
                'Using existing S3 bucket: MyBucket',
                mock_stdout.getvalue())

    def test_output_create_bucket(self):
        name = 'MyBucket/MyPrefix'
        self.s3_client.head_bucket.side_effect = self.bucket_no_exists_error
        self.s3_client._endpoint.region_name = 'us-east-1'
        with mock.patch('sys.stdout', StringIO()) as mock_stdout:
            self.helper.prepare_bucket(name)
            self.assertIn(
                'Using new S3 bucket: MyBucket',
                mock_stdout.getvalue())


class TestSNSTopicHelper(unittest.TestCase):
    def setUp(self):
        self.sns_client = mock.Mock()
        self.helper = SNSTopicHelper(self.sns_client)

    def test_sns_topic_by_name(self):
        name = 'mysnstopic'
        self.sns_client.create_topic.return_value = {'TopicArn': 'myARN'}
        sns_arn = self.helper.prepare_topic(name)
        # Ensure that the topic was create and returned the expected arn
        self.assertTrue(self.sns_client.create_topic.called)
        self.assertEqual(sns_arn, 'myARN')

    def test_sns_topic_by_arn(self):
        name = 'arn:aws:sns:us-east-1:934212987125:config'
        sns_arn = self.helper.prepare_topic(name)
        # Ensure that the topic was not created and returned the expected arn
        self.assertFalse(self.sns_client.create_topic.called)
        self.assertEqual(sns_arn, name)

    def test_output_existing_topic(self):
        name = 'mysnstopic'
        self.sns_client.create_topic.return_value = {'TopicArn': 'myARN'}
        with mock.patch('sys.stdout', StringIO()) as mock_stdout:
            self.helper.prepare_topic(name)
            self.assertIn(
                'Using new SNS topic: myARN',
                mock_stdout.getvalue())

    def test_output_new_topic(self):
        name = 'arn:aws:sns:us-east-1:934212987125:config'
        with mock.patch('sys.stdout', StringIO()) as mock_stdout:
            self.helper.prepare_topic(name)
            self.assertIn(
                'Using existing SNS topic: %s' % name,
                mock_stdout.getvalue())


class TestSubscribeCommand(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()

        # Set up the client mocks.
        self.s3_client = mock.Mock()
        self.sns_client = mock.Mock()
        self.config_client = mock.Mock()
        self.config_client.describe_configuration_recorders.return_value = \
            {'ConfigurationRecorders': []}
        self.config_client.describe_delivery_channels.return_value = \
            {'DeliveryChannels': []}

        self.session.create_client.side_effect = [
            self.s3_client,
            self.sns_client,
            self.config_client
        ]

        self.parsed_args = mock.Mock()
        self.parsed_args.s3_bucket = 'MyBucket/MyPrefix'
        self.parsed_args.sns_topic = \
            'arn:aws:sns:us-east-1:934212987125:config'
        self.parsed_args.iam_role = 'arn:aws:iam::1234556789:role/config'

        self.parsed_globals = mock.Mock()

        self.cmd = SubscribeCommand(self.session)

    def test_setup_clients(self):
        self.parsed_globals.verify_ssl = True
        self.parsed_globals.region = 'us-east-1'
        self.parsed_globals.endpoint_url = 'http://myendpoint.com'

        self.cmd._run_main(self.parsed_args, self.parsed_globals)

        # Check to see that the clients were created correctly
        self.session.create_client.assert_any_call(
            's3',
            verify=self.parsed_globals.verify_ssl,
            region_name=self.parsed_globals.region,
        )
        self.session.create_client.assert_any_call(
            'sns',
            verify=self.parsed_globals.verify_ssl,
            region_name=self.parsed_globals.region,
        )
        self.session.create_client.assert_any_call(
            'config',
            verify=self.parsed_globals.verify_ssl,
            region_name=self.parsed_globals.region,
            endpoint_url=self.parsed_globals.endpoint_url
        )

    def test_subscribe(self):
        self.cmd._run_main(self.parsed_args, self.parsed_globals)

        # Check the call made to put configuration recorder.
        self.config_client.put_configuration_recorder.assert_called_with(
            ConfigurationRecorder={
                'name': 'default',
                'roleARN': self.parsed_args.iam_role
            }
        )

        # Check the call made to put delivery channel.
        self.config_client.put_delivery_channel.assert_called_with(
            DeliveryChannel={
                'name': 'default',
                's3BucketName': 'MyBucket',
                'snsTopicARN': self.parsed_args.sns_topic,
                's3KeyPrefix': 'MyPrefix'
            }
        )

        # Check the call made to start configuration recorder.
        self.config_client.start_configuration_recorder.assert_called_with(
            ConfigurationRecorderName='default'
        )

        # Check that the describe delivery channel and configuration recorder
        # methods were called.
        self.assertTrue(
            self.config_client.describe_configuration_recorders.called
        )
        self.assertTrue(self.config_client.describe_delivery_channels.called)
