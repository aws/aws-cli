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
import json

from mock import ANY, Mock, call, patch
from botocore.client import ClientError
from botocore.session import Session

from tests.unit.test_clidriver import FakeSession
from awscli.compat import six
from awscli.customizations import cloudtrail
from awscli.testutils import BaseAWSCommandParamsTest
from awscli.testutils import unittest, temporary_file


class TestCloudTrailPlumbing(unittest.TestCase):
    def test_initialization_registers_injector(self):
        cli = Mock()
        cloudtrail.initialize(cli)
        cli.register.assert_called_with('building-command-table.cloudtrail',
                                        cloudtrail.inject_commands)

    def test_injection_adds_two_commands_to_cmd_table(self):
        command_table = {}
        session = Mock()
        cloudtrail.inject_commands(command_table, session)
        self.assertIn('create-subscription', command_table)
        self.assertIn('update-subscription', command_table)


class TestCreateSubscription(BaseAWSCommandParamsTest):
    def test_create_subscription_has_zero_rc(self):
        command = (
            'cloudtrail create-subscription --s3-use-bucket foo --name bar')
        stdout = self.run_cmd(command, expected_rc=0)[0]
        # We don't want to overspecify here, but we'll do a quick check to make
        # sure it says log delivery is happening.
        self.assertIn('Logs will be delivered to foo', stdout)

    @patch.object(Session, 'create_client')
    def test_policy_from_paramfile(self, create_client_mock):
        client = Mock()
        # S3 mock calls
        client.get_user.return_value = {'User': {'Arn': ':::::'}}
        client.head_bucket.side_effect = ClientError(
            {'Error': {'Code': 404, 'Message': ''}}, 'HeadBucket')
        # CloudTrail mock call
        client.describe_trails.return_value = {}
        create_client_mock.return_value = client

        policy = '{"Statement": []}'

        with temporary_file('w') as f:
            f.write(policy)
            f.flush()
            command = (
                'cloudtrail create-subscription --s3-new-bucket foo '
                '--name bar --s3-custom-policy file://{0}'.format(f.name))
            self.run_cmd(command, expected_rc=0)

        # Ensure that the *contents* of the file are sent as the policy
        # parameter to S3.
        client.put_bucket_policy.assert_called_with(
            Bucket='foo', Policy=policy)


class TestCloudTrailCommand(unittest.TestCase):
    def setUp(self):
        self.session = FakeSession({'config_file': 'myconfigfile'})
        self.subscribe = cloudtrail.CloudTrailSubscribe(self.session)
        self.subscribe.region_name = 'us-east-1'

        self.subscribe.iam = Mock()
        self.subscribe.iam.get_user = Mock(
            return_value={'User': {'Arn': '::::123:456'}})

        self.subscribe.s3 = Mock()
        self.subscribe.s3.meta.region_name = 'us-east-1'
        policy_template = six.BytesIO(six.b(u'{"Statement": []}'))
        self.subscribe.s3.get_object = Mock(
            return_value={'Body': policy_template})
        self.subscribe.s3.head_bucket.return_value = {}

        self.subscribe.sns = Mock()
        self.subscribe.sns.meta.region_name = 'us-east-1'
        self.subscribe.sns.list_topics = Mock(
            return_value={'Topics': [{'TopicArn': ':test2'}]})
        self.subscribe.sns.create_topic = Mock(
            return_value={'TopicArn': 'foo'})
        self.subscribe.sns.get_topic_attributes = Mock(
            return_value={'Attributes': {'Policy': '{"Statement": []}'}})

    def test_clients_all_from_same_session(self):
        session = Mock()
        subscribe_command = cloudtrail.CloudTrailSubscribe(session)
        parsed_globals = Mock(region=None, verify_ssl=None,
                              endpoint_url=None)
        subscribe_command.setup_services(None, parsed_globals)
        create_client_calls = session.create_client.call_args_list
        self.assertEqual(
            create_client_calls, [
                call('iam', verify=None, region_name=None),
                call('s3', verify=None, region_name=None),
                call('sns', verify=None, region_name=None),
                call('cloudtrail', verify=None, region_name=None),
            ]
        )
        # We should also remove the error handler for S3.
        # This can be removed once the client switchover is done.
        subscribe_command.s3.meta.events.unregister.assert_called_with(
            'after-call', unique_id='awscli-error-handler')

    def test_endpoint_url_is_only_used_for_cloudtrail(self):
        endpoint_url = 'https://mycloudtrail.awsamazon.com/'
        session = Mock()
        subscribe_command = cloudtrail.CloudTrailSubscribe(session)
        parsed_globals = Mock(region=None, verify_ssl=None,
                              endpoint_url=endpoint_url)
        subscribe_command.setup_services(None, parsed_globals)
        create_client_calls = session.create_client.call_args_list
        self.assertEqual(
            create_client_calls, [
                call('iam', verify=None, region_name=None),
                call('s3', verify=None, region_name=None),
                call('sns', verify=None, region_name=None),
                # Here we should inject the endpoint_url only for cloudtrail.
                call('cloudtrail', verify=None, region_name=None,
                     endpoint_url=endpoint_url),
            ]
        )

    def test_s3_create(self):
        iam = self.subscribe.iam
        s3 = self.subscribe.s3
        s3.head_bucket.side_effect = ClientError(
            {'Error': {'Code': '404', 'Message': ''}}, 'HeadBucket')

        self.subscribe.setup_new_bucket('test', 'logs')

        iam.get_user.assert_called()

        s3.get_object.assert_called()
        s3.create_bucket.assert_called()
        s3.put_bucket_policy.assert_called()

        s3.delete_bucket.assert_not_called()

        args, kwargs = s3.create_bucket.call_args
        self.assertNotIn('create_bucket_configuration', kwargs)

    def test_s3_uses_regionalized_policy(self):
        s3 = self.subscribe.s3
        s3.head_bucket.side_effect = ClientError(
            {'Error': {'Code': '404', 'Message': ''}}, 'HeadBucket')

        self.subscribe.setup_new_bucket('test', 'logs')

        s3.get_object.assert_called_with(
            Bucket='awscloudtrail-policy-us-east-1', Key=ANY)

    def test_s3_create_non_us_east_1(self):
        # Because this is outside of us-east-1, it should create
        # a bucket configuration with a location constraint.
        s3 = self.subscribe.s3
        self.subscribe.region_name = 'us-west-2'
        s3.head_bucket.side_effect = ClientError(
            {'Error': {'Code': '404', 'Message': ''}}, 'HeadBucket')

        self.subscribe.setup_new_bucket('test', 'logs')

        args, kwargs = s3.create_bucket.call_args
        self.assertIn('CreateBucketConfiguration', kwargs)

        bucket_config = kwargs['CreateBucketConfiguration']
        self.assertEqual(bucket_config['LocationConstraint'],
                         'us-west-2')

    def test_s3_create_already_exists(self):
        with self.assertRaises(Exception):
            self.subscribe.setup_new_bucket('test2', 'logs')

    def test_s3_custom_policy(self):
        s3 = self.subscribe.s3
        s3.head_bucket.side_effect = ClientError(
            {'Error': {'Code': '404', 'Message': ''}}, 'HeadBucket')

        self.subscribe.setup_new_bucket('test', 'logs', custom_policy='{}')

        s3.get_object.assert_not_called()
        s3.put_bucket_policy.assert_called_with(Bucket='test', Policy='{}')

    def test_s3_create_set_policy_fail(self):
        s3 = self.subscribe.s3
        orig = s3.put_bucket_policy
        s3.put_bucket_policy = Mock(side_effect=Exception('Error!'))

        with self.assertRaises(Exception):
            self.subscribe.setup_new_bucket('test', 'logs')

        s3.create_bucket.assert_called()
        s3.put_bucket_policy.assert_called()
        s3.DeleteBucket.assert_called()

        s3.put_bucket_policy = orig

    def test_s3_get_policy_fail(self):
        self.subscribe.s3.get_object = Mock(side_effect=Exception('Foo!'))

        with self.assertRaises(cloudtrail.CloudTrailError) as cm:
            self.subscribe.setup_new_bucket('test', 'logs')

        # Exception should contain its custom message, the region
        # where there is an issue, and the original exception message.
        self.assertIn('us-east-1', str(cm.exception))
        self.assertIn('Foo!', str(cm.exception))

    def test_get_policy_read_timeout(self):
        response = {
            'Body': Mock()
        }
        response['Body'].read.side_effect = Exception('Error!')
        self.subscribe.s3.get_object.return_value = response

        with self.assertRaises(cloudtrail.CloudTrailError):
            self.subscribe.setup_new_bucket('test', 'logs')

    def test_sns_get_policy_fail(self):
        self.subscribe.s3.get_object = Mock(side_effect=Exception('Error!'))

        with self.assertRaises(Exception):
            self.subscribe.setup_new_bucket('test', 'logs')

    def test_sns_create(self):
        s3 = self.subscribe.s3
        sns = self.subscribe.sns

        self.subscribe.setup_new_topic('test')

        s3.get_object.assert_called()
        sns.list_topics.assert_called()
        sns.create_topic.assert_called()
        sns.set_topic_attributes.assert_called()

        sns.delete_topic.assert_not_called()

    def test_sns_uses_regionalized_policy(self):
        s3 = self.subscribe.s3

        self.subscribe.setup_new_topic('test')

        s3.get_object.assert_called_with(
            Bucket='awscloudtrail-policy-us-east-1', Key=ANY)

    def test_sns_custom_policy(self):
        s3 = self.subscribe.s3
        sns = self.subscribe.sns
        sns.get_topic_attributes.return_value = {
            'Attributes': {
                'Policy': '{"Statement": []}'
            }
        }

        policy = '{"Statement": []}'

        self.subscribe.setup_new_topic('test', custom_policy=policy)

        s3.get_object.assert_not_called()
        sns.set_topic_attributes.assert_called_with(
          TopicArn=ANY, AttributeName='Policy', AttributeValue=policy)

    def test_sns_create_already_exists(self):
        with self.assertRaises(Exception):
            self.subscribe.setup_new_topic('test2')

    def test_cloudtrail_new_call_format(self):
        self.subscribe.cloudtrail = Mock()
        self.subscribe.cloudtrail.create_trail = Mock(return_value={})
        self.subscribe.cloudtrail.describe_trail = Mock(return_value={})

        self.subscribe.upsert_cloudtrail_config('test', 'bucket', 'prefix',
                                                'topic', True)

        self.subscribe.cloudtrail.create_trail.assert_called_with(
            Name='test',
            S3BucketName='bucket',
            S3KeyPrefix='prefix',
            SnsTopicName='topic',
            IncludeGlobalServiceEvents=True
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
