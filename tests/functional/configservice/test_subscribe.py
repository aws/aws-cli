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
from awscli.testutils import BaseAWSCommandParamsTest


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
        # S3 operations
        self.assertEqual(self.operations_called[0][0].name, 'HeadBucket')
        self.assertEqual(self.operations_called[0][1], {'Bucket': 'mybucket'})

        # SNS operations
        self.assertEqual(self.operations_called[1][0].name, 'CreateTopic')
        self.assertEqual(self.operations_called[1][1], {'Name': 'mytopic'})

        # Config operations
        self.assertEqual(
            self.operations_called[2][0].name,
            'PutConfigurationRecorder')
        self.assertEqual(
            self.operations_called[2][1],
            {'ConfigurationRecorder': {'name': 'default', 'roleARN': 'myrole'}}
        )
        self.assertEqual(
            self.operations_called[3][0].name,
            'PutDeliveryChannel')
        self.assertEqual(
            self.operations_called[3][1],
            {'DeliveryChannel': {
                'name': 'default',
                's3BucketName': 'mybucket',
                'snsTopicARN': 'my-topic-arn'}}
        )
        self.assertEqual(
            self.operations_called[4][0].name,
            'StartConfigurationRecorder')
        self.assertEqual(
            self.operations_called[4][1],
            {'ConfigurationRecorderName': 'default'}
        )
        self.assertEqual(
            self.operations_called[5][0].name,
            'DescribeConfigurationRecorders')
        self.assertEqual(self.operations_called[5][1], {})
        self.assertEqual(
            self.operations_called[6][0].name,
            'DescribeDeliveryChannels')
        self.assertEqual(self.operations_called[6][1], {})

    def test_subscribe_when_bucket_exists_and_sns_topic_arn_provided(self):
        self.parsed_responses.pop(1)
        self.prefix += ' --s3-bucket mybucket --sns-topic arn:mytopic'
        self.prefix += ' --iam-role myrole'
        self.run_cmd(self.prefix)

        self.assertEqual(len(self.operations_called), 6)
        # S3 operations
        self.assertEqual(self.operations_called[0][0].name, 'HeadBucket')
        self.assertEqual(self.operations_called[0][1], {'Bucket': 'mybucket'})

        # Config operations
        self.assertEqual(
            self.operations_called[1][0].name,
            'PutConfigurationRecorder')
        self.assertEqual(
            self.operations_called[1][1],
            {'ConfigurationRecorder': {'name': 'default', 'roleARN': 'myrole'}}
        )
        self.assertEqual(
            self.operations_called[2][0].name,
            'PutDeliveryChannel')
        self.assertEqual(
            self.operations_called[2][1],
            {'DeliveryChannel': {
                'name': 'default',
                's3BucketName': 'mybucket',
                'snsTopicARN': 'arn:mytopic'}}
        )
        self.assertEqual(
            self.operations_called[3][0].name,
            'StartConfigurationRecorder')
        self.assertEqual(
            self.operations_called[3][1],
            {'ConfigurationRecorderName': 'default'}
        )
        self.assertEqual(
            self.operations_called[4][0].name,
            'DescribeConfigurationRecorders')
        self.assertEqual(self.operations_called[4][1], {})
        self.assertEqual(
            self.operations_called[5][0].name,
            'DescribeDeliveryChannels')
        self.assertEqual(self.operations_called[5][1], {})

    def test_subscribe_when_bucket_needs_to_be_created(self):
        # Make the HeadObject request fail now and should try to create a new
        # bucket.
        self.parsed_responses = None
        self.http_response.status_code = 404
        self.parsed_response = {'Error': {'Code': 404, 'Message': ''}}

        self.prefix += ' --s3-bucket mybucket --sns-topic arn:mytopic'
        self.prefix += ' --iam-role myrole'
        self.run_cmd(self.prefix, expected_rc=255)
        # This will fail because there is no current way to specify
        # a change in status code in BaseAWSCommandParamsTest
        # As of now only one status code applies to all parsed responses.
        # Therefore the CreateBucket will be the one that receives the 404.
        # But it does not matter because we are just checking that the bucket
        # is attempted to be made if we determine the bucket does not exist
        self.assertEqual(len(self.operations_called), 2)

        self.assertEqual(self.operations_called[0][0].name, 'HeadBucket')
        self.assertEqual(self.operations_called[0][1], {'Bucket': 'mybucket'})
        self.assertEqual(self.operations_called[1][0].name, 'CreateBucket')
        self.assertEqual(
            self.operations_called[1][1]['Bucket'], 'mybucket')
