# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.testutils import BaseAWSCommandParamsTest
from awscli.customizations.configservice.subscribe import S3BucketHelper


class TestSubscribe(BaseAWSCommandParamsTest):
    prefix = 'configservice subscribe'

    def setUp(self):
        super(TestSubscribe, self).setUp()
        self.parsed_responses = [
            {},  # S3 HeadBucket
            {'TopicArn': 'my-topic-arn'},  # SNS CreateTopic
            {},  # PutConfigurationRecorder
            {},  # PutDeliveryChannel
            {},  # StartConfigurationRecorder
            {'ConfigurationRecorders': {}},  # DescribeConfigurationRecorders
            {'DeliveryChannels': {}}  # DescribeDeliveryChannels
        ]

    def test_subscribe_when_bucket_exists_and_new_sns_topic(self):
        self.prefix += ' --s3-bucket mybucket --sns-topic mytopic'
        self.prefix += ' --iam-role myrole'
        self.run_cmd(self.prefix)

        self.assertEqual(len(self.operations_called), 7)
        list_of_operation_names_called = []
        list_of_parameters_called = []
        for operation_called in self.operations_called:
            list_of_operation_names_called.append(operation_called[0].name)
            list_of_parameters_called.append(operation_called[1])

        self.assertEqual(
            list_of_operation_names_called, [
                'HeadBucket',
                'CreateTopic',
                'PutConfigurationRecorder',
                'PutDeliveryChannel',
                'StartConfigurationRecorder',
                'DescribeConfigurationRecorders',
                'DescribeDeliveryChannels'
            ]
        )
        self.assertEqual(
            list_of_parameters_called, [
                {'Bucket': 'mybucket'},  # S3 HeadBucket
                {'Name': 'mytopic'},  # SNS CreateTopic
                {'ConfigurationRecorder': {  # PutConfigurationRecorder
                    'name': 'default', 'roleARN': 'myrole'}},
                {'DeliveryChannel': {  # PutDeliveryChannel
                    'name': 'default',
                    's3BucketName': 'mybucket',
                    'snsTopicARN': 'my-topic-arn'}},
                # StartConfigurationRecorder
                {'ConfigurationRecorderName': 'default'},
                {},  # DescribeConfigurationRecorders
                {}  # DescribeDeliveryChannels
            ]
        )

    def test_subscribe_when_bucket_exists_and_sns_topic_arn_provided(self):
        self.parsed_responses.pop(1)
        self.prefix += ' --s3-bucket mybucket --sns-topic arn:mytopic'
        self.prefix += ' --iam-role myrole'
        self.run_cmd(self.prefix)

        self.assertEqual(len(self.operations_called), 6)
        list_of_operation_names_called = []
        list_of_parameters_called = []
        for operation_called in self.operations_called:
            list_of_operation_names_called.append(operation_called[0].name)
            list_of_parameters_called.append(operation_called[1])

        self.assertEqual(
            list_of_operation_names_called, [
                'HeadBucket',
                'PutConfigurationRecorder',
                'PutDeliveryChannel',
                'StartConfigurationRecorder',
                'DescribeConfigurationRecorders',
                'DescribeDeliveryChannels'
            ]
        )
        self.assertEqual(
            list_of_parameters_called, [
                {'Bucket': 'mybucket'},  # S3 HeadBucket
                {'ConfigurationRecorder': {  # PutConfigurationRecorder
                    'name': 'default', 'roleARN': 'myrole'}},
                {'DeliveryChannel': {  # PutDeliveryChannel
                    'name': 'default',
                    's3BucketName': 'mybucket',
                    'snsTopicARN': 'arn:mytopic'}},
                # StartConfigurationRecorder
                {'ConfigurationRecorderName': 'default'},
                {},  # DescribeConfigurationRecorders
                {}  # DescribeDeliveryChannels
            ]
        )

    def test_subscribe_when_bucket_needs_to_be_created(self):
        # TODO: fix this patch when we have a better way to stub out responses
        with mock.patch('botocore.endpoint.Endpoint._send') as \
                http_session_send_patch:
            # Mock for HeadBucket request
            head_bucket_response = mock.Mock()
            head_bucket_response.status_code = 404
            head_bucket_response.content = b''
            head_bucket_response.headers = {}

            # Mock for CreateBucket request
            create_bucket_response = mock.Mock()
            create_bucket_response.status_code = 200
            create_bucket_response.content = b''
            create_bucket_response.headers = {}

            http_session_send_patch.side_effect = [
                head_bucket_response, create_bucket_response
            ]

            s3_client = self.driver.session.create_client('s3')
            bucket_helper = S3BucketHelper(s3_client)
            bucket_helper.prepare_bucket('mybucket')
            send_call_list = http_session_send_patch.call_args_list
            self.assertEqual(send_call_list[0][0][0].method, 'HEAD')
            # Since the HeadObject fails with 404, the CreateBucket which is
            # is a PUT request should be made.
            self.assertEqual(send_call_list[1][0][0].method, 'PUT')
