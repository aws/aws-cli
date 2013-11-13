# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import io

from awscli.customizations.cloudtrail import CloudTrailSubscribe
from awscli.customizations.service import Service
from mock import Mock
from tests.unit.customizations.test_configure import FakeSession
from tests import unittest


class TestCloudTrail(unittest.TestCase):
    def setUp(self):
        self.session = FakeSession({'config_file': 'myconfigfile'})
        self.subscribe = CloudTrailSubscribe(self.session)

        self.subscribe.iam = Mock()
        self.subscribe.iam.GetUser = Mock(
            return_value={'User': {'Arn': '::::123:456'}})

        self.subscribe.s3 = Mock()
        self.subscribe.s3.endpoint = Mock()
        self.subscribe.s3.endpoint.region_name = 'us-east-1'
        policy_template = io.StringIO(initial_value=u'')
        self.subscribe.s3.GetObject = Mock(
            return_value={'Body': policy_template})
        self.subscribe.s3.ListBuckets = Mock(
            return_value={'Buckets': [{'Name': 'test2'}]})

        self.subscribe.sns = Mock()
        self.subscribe.sns.endpoint = Mock()
        self.subscribe.sns.endpoint.region_name = 'us-east-1'
        self.subscribe.sns.ListTopics = Mock(
            return_value={'Topics': [{'TopicArn': ':test2'}]})
        self.subscribe.sns.CreateTopic = Mock(
            return_value={'TopicArn': 'foo'})

    def test_s3_create(self):
        iam = self.subscribe.iam
        s3 = self.subscribe.s3

        self.subscribe.setup_new_bucket('test', 'logs')

        iam.GetUser.assert_called()

        s3.GetObject.assert_called()
        s3.ListBuckets.assert_called()
        s3.CreateBucket.assert_called()
        s3.PutBucketPolicy.assert_called()

        s3.DeleteBucket.assert_not_called()

    def test_s3_create_already_exists(self):
        with self.assertRaises(Exception):
            self.subscribe.setup_new_bucket('test2', 'logs')

    def test_s3_create_set_policy_fail(self):
        s3 = self.subscribe.s3
        orig = s3.PutBucketPolicy
        s3.PutBucketPolicy = Mock(side_effect=Exception('Error!'))

        with self.assertRaises(Exception):
            self.subscribe.setup_new_bucket('test', 'logs')

        s3.CreateBucket.assert_called()
        s3.PutBucketPolicy.assert_called()
        s3.DeleteBucket.assert_called()

        s3.PutBucketPolicy = orig

    def test_get_policy_fail(self):
        orig = self.subscribe.s3.GetObject
        self.subscribe.s3.GetObject = Mock(side_effect=Exception('Error!'))

        with self.assertRaises(Exception):
            self.subscribe.setup_new_bucket('test', 'logs')

        self.subscribe.s3.GetObject = orig

    def test_sns_create(self):
        s3 = self.subscribe.s3
        sns = self.subscribe.sns

        self.subscribe.setup_new_topic('test')

        s3.GetObject.assert_called()
        sns.ListTopics.assert_called()
        sns.CreateTopic.assert_called()
        sns.SetTopicAttributes.assert_called()

        sns.DeleteTopic.assert_not_called()

    def test_sns_create_already_exists(self):
        with self.assertRaises(Exception):
            self.subscribe.setup_new_topic('test2')
