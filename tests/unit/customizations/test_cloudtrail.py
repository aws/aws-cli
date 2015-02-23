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
import argparse
import botocore.session
import json
import os
from awscli.compat import six

from awscli.customizations import cloudtrail
from awscli.customizations.cloudtrail import CloudTrailSubscribe
from awscli.customizations.service import Service
from mock import ANY, Mock, patch
from awscli.testutils import BaseAWSCommandParamsTest
from tests.unit.test_clidriver import FakeSession
from awscli.testutils import unittest


class TestCloudTrail(unittest.TestCase):
    def setUp(self):
        self.session = FakeSession({'config_file': 'myconfigfile'})
        self.subscribe = CloudTrailSubscribe(self.session)
        self.subscribe.region_name = 'us-east-1'

        self.subscribe.iam = Mock()
        self.subscribe.iam.GetUser = Mock(
            return_value={'User': {'Arn': '::::123:456'}})

        self.subscribe.s3 = Mock()
        self.subscribe.s3.endpoint = Mock()
        self.subscribe.s3.endpoint.region_name = 'us-east-1'
        policy_template = six.BytesIO(six.b(u'{"Statement": []}'))
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
        self.subscribe.sns.GetTopicAttributes = Mock(
            return_value={'Attributes': {'Policy': '{"Statement": []}'}})

    def test_setup_services(self):
        parsed_args = []
        parsed_globals = argparse.Namespace()
        parsed_globals.region = 'us-east-1'
        parsed_globals.verify_ssl = 'foo'
        parsed_globals.endpoint_url = 'https://cloudtrail.aws.com'

        ref_args = {
            'region_name': parsed_globals.region,
            'verify': parsed_globals.verify_ssl,
            'endpoint_url': None
        }

        # Reset some of the mocks because we need some introspection on the
        # session.
        fake_service = Mock()
        self.session = Mock()
        self.session.get_service.return_value = fake_service
        self.subscribe = CloudTrailSubscribe(self.session)

        self.subscribe.setup_services(parsed_args, parsed_globals)

        get_service_call_args = self.session.get_service.call_args_list
        endpoint_call_args = fake_service.get_endpoint.call_args_list

        # Ensure all of the services got called.
        self.assertEqual('iam', get_service_call_args[0][0][0])
        self.assertEqual('s3', get_service_call_args[1][0][0])
        self.assertEqual('sns', get_service_call_args[2][0][0])
        self.assertEqual('cloudtrail', get_service_call_args[3][0][0])

        # Make sure the endpoints were called correctly
        # The order is iam, s3, sns, cloudtrail based on ``get_service`` calls
        # from above.
        self.assertEqual(endpoint_call_args[0][1], ref_args)
        self.assertEqual(endpoint_call_args[1][1], ref_args)
        self.assertEqual(endpoint_call_args[2][1], ref_args)
        # CloudTrail should be using the endpoint.
        ref_args['endpoint_url'] = parsed_globals.endpoint_url
        self.assertEqual(endpoint_call_args[3][1], ref_args)

        # Ensure a region name was set on the command class
        self.assertEqual(self.subscribe.region_name,
                         fake_service.get_endpoint.return_value.region_name)

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

        args, kwargs = s3.CreateBucket.call_args
        self.assertNotIn('create_bucket_configuration', kwargs)

    def test_s3_uses_regionalized_policy(self):
        s3 = self.subscribe.s3

        self.subscribe.setup_new_bucket('test', 'logs')

        s3.GetObject.assert_called_with(
            bucket='awscloudtrail-policy-us-east-1', key=ANY)

    def test_s3_create_non_us_east_1(self):
        # Because this is outside of us-east-1, it should create
        # a bucket configuration with a location constraint.
        s3 = self.subscribe.s3
        self.subscribe.region_name = 'us-west-2'

        self.subscribe.setup_new_bucket('test', 'logs')

        args, kwargs = s3.CreateBucket.call_args
        self.assertIn('create_bucket_configuration', kwargs)

        bucket_config = kwargs['create_bucket_configuration']
        self.assertEqual(bucket_config['LocationConstraint'],
                         'us-west-2')

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

    def test_s3_get_policy_fail(self):
        self.subscribe.s3.GetObject = Mock(side_effect=Exception('Error!'))

        with self.assertRaises(Exception):
            self.subscribe.setup_new_bucket('test', 'logs')

    def test_s3_get_policy_logs_messages(self):
        cloudtrail.LOG = Mock()
        self.subscribe.s3.GetObject = Mock(side_effect=Exception('Error!'))

        try:
            self.subscribe.setup_new_bucket('test', 'logs')
        except:
            pass

        self.assertIn(
            'Unable to get regional policy template for region',
            cloudtrail.LOG.error.call_args[0][0])
        self.assertEqual('us-east-1', cloudtrail.LOG.error.call_args[0][1])

    def test_get_policy_read_timeout(self):
        response = {
            'Body': Mock()
        }
        response['Body'].read.side_effect = Exception('Error!')
        self.subscribe.s3.GetObject.return_value = response

        with self.assertRaises(Exception):
            self.subscribe.setup_new_bucket('test', 'logs')

    def test_sns_get_policy_fail(self):
        self.subscribe.s3.GetObject = Mock(side_effect=Exception('Error!'))

        with self.assertRaises(Exception):
            self.subscribe.setup_new_bucket('test', 'logs')

    def test_sns_create(self):
        s3 = self.subscribe.s3
        sns = self.subscribe.sns

        self.subscribe.setup_new_topic('test')

        s3.GetObject.assert_called()
        sns.ListTopics.assert_called()
        sns.CreateTopic.assert_called()
        sns.SetTopicAttributes.assert_called()

        sns.DeleteTopic.assert_not_called()

    def test_sns_uses_regionalized_policy(self):
        s3 = self.subscribe.s3

        self.subscribe.setup_new_topic('test')

        s3.GetObject.assert_called_with(
            bucket='awscloudtrail-policy-us-east-1', key=ANY)

    def test_sns_create_already_exists(self):
        with self.assertRaises(Exception):
            self.subscribe.setup_new_topic('test2')

    def test_cloudtrail_new_call_format(self):
        self.subscribe.cloudtrail = Mock()
        self.subscribe.cloudtrail.CreateTrail = Mock(return_value={})
        self.subscribe.cloudtrail.DescribeTrail = Mock(return_value={})

        self.subscribe.upsert_cloudtrail_config('test', 'bucket', 'prefix',
                                                'topic', True)

        self.subscribe.cloudtrail.CreateTrail.assert_called_with(
            name='test',
            s3_bucket_name='bucket',
            s3_key_prefix='prefix',
            sns_topic_name='topic',
            include_global_service_events=True
        )

    def test_sns_policy_merge(self):
        left = '''
{
   "Version":"2008-10-17",
   "Id":"us-east-1/698519295917/test__default_policy_ID",
   "Statement":[
      {
         "Effect":"Allow",
         "Sid":"us-east-1/698519295917/test__default_statement_ID",
         "Principal":{
            "AWS":"*"
         },
         "Action":[
            "SNS:GetTopicAttributes",
            "SNS:SetTopicAttributes",
            "SNS:AddPermission",
            "SNS:RemovePermission",
            "SNS:DeleteTopic",
            "SNS:Subscribe",
            "SNS:ListSubscriptionsByTopic",
            "SNS:Publish",
            "SNS:Receive"
         ],
         "Resource":"arn:aws:sns:us-east-1:698519295917:test",
         "Condition":{
            "StringLike":{
               "AWS:SourceArn":"arn:aws:*:*:698519295917:*"
            }
         }
      }
   ]
}'''
        right = '''
{
   "Version":"2008-10-17",
   "Id":"us-east-1/698519295917/test_foo",
   "Statement":[
      {
         "Effect":"Allow",
         "Sid":"us-east-1/698519295917/test_foo_ID",
         "Principal":{
            "AWS":"*"
         },
         "Action":[
            "SNS:GetTopicAttributes",
            "SNS:SetTopicAttributes",
            "SNS:AddPermission",
            "SNS:RemovePermission",
            "SNS:DeleteTopic",
            "SNS:Subscribe",
            "SNS:ListSubscriptionsByTopic",
            "SNS:Publish",
            "SNS:Receive"
         ],
         "Resource":"arn:aws:sns:us-east-1:698519295917:test",
         "Condition":{
            "StringLike":{
               "AWS:SourceArn":"arn:aws:*:*:698519295917:*"
            }
         }
      }
   ]
}'''
        expected = '''
{
   "Version":"2008-10-17",
   "Id":"us-east-1/698519295917/test__default_policy_ID",
   "Statement":[
      {
         "Effect":"Allow",
         "Sid":"us-east-1/698519295917/test__default_statement_ID",
         "Principal":{
            "AWS":"*"
         },
         "Action":[
            "SNS:GetTopicAttributes",
            "SNS:SetTopicAttributes",
            "SNS:AddPermission",
            "SNS:RemovePermission",
            "SNS:DeleteTopic",
            "SNS:Subscribe",
            "SNS:ListSubscriptionsByTopic",
            "SNS:Publish",
            "SNS:Receive"
         ],
         "Resource":"arn:aws:sns:us-east-1:698519295917:test",
         "Condition":{
            "StringLike":{
               "AWS:SourceArn":"arn:aws:*:*:698519295917:*"
            }
         }
      },
      {
         "Effect":"Allow",
         "Sid":"us-east-1/698519295917/test_foo_ID",
         "Principal":{
            "AWS":"*"
         },
         "Action":[
            "SNS:GetTopicAttributes",
            "SNS:SetTopicAttributes",
            "SNS:AddPermission",
            "SNS:RemovePermission",
            "SNS:DeleteTopic",
            "SNS:Subscribe",
            "SNS:ListSubscriptionsByTopic",
            "SNS:Publish",
            "SNS:Receive"
         ],
         "Resource":"arn:aws:sns:us-east-1:698519295917:test",
         "Condition":{
            "StringLike":{
               "AWS:SourceArn":"arn:aws:*:*:698519295917:*"
            }
         }
      }
   ]
}'''

        merged = self.subscribe.merge_sns_policy(left, right)

        self.assertEqual(json.loads(expected), json.loads(merged))


class TestCloudTrailSessions(BaseAWSCommandParamsTest):
    def test_sessions(self):
        """
        Make sure that the session passed to our custom command
        is the same session used when making service calls.
        """
        # Get a new session we will use to test
        driver = self.driver

        def _mock_call(subscribe, *args, **kwargs):
            # Store the subscribe command for assertions
            # This works because the first argument to an
            # instance method is always the instance itself.
            self.subscribe = subscribe

        with patch.object(CloudTrailSubscribe, '_call', _mock_call):
            driver.main('cloudtrail create-subscription --name test --s3-use-bucket test'.split())

            # Test the session that is used in dependent services
            subscribe = self.subscribe
            self.assertEqual(driver.session, subscribe.iam.session)
            self.assertEqual(driver.session, subscribe.s3.session)
            self.assertEqual(driver.session, subscribe.sns.session)
            self.assertEqual(driver.session, subscribe.cloudtrail.session)
