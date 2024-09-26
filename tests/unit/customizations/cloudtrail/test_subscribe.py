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

from botocore.client import ClientError
from botocore.session import Session

from tests.unit.test_clidriver import FakeSession
from awscli.customizations.cloudtrail.subscribe import CloudTrailError, CloudTrailSubscribe
from awscli.compat import BytesIO
from awscli.testutils import BaseAWSCommandParamsTest
from awscli.testutils import mock, unittest, temporary_file


class TestCreateSubscription(BaseAWSCommandParamsTest):
    def test_create_subscription_has_zero_rc(self):
        command = (
            'cloudtrail create-subscription --s3-use-bucket foo --name bar')
        stdout = self.run_cmd(command, expected_rc=0)[0]
        # We don't want to overspecify here, but we'll do a quick check to make
        # sure it says log delivery is happening.
        self.assertIn('Logs will be delivered to foo', stdout)

    @mock.patch.object(Session, 'create_client')
    def test_policy_from_paramfile(self, create_client_mock):
        client = mock.Mock()
        # S3 mock calls
        client.get_caller_identity.return_value = {'Account': ''}
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
        self.subscribe = CloudTrailSubscribe(self.session)
        self.subscribe.region_name = 'us-east-1'

        self.subscribe.sts = mock.Mock()
        self.subscribe.sts.get_caller_identity = mock.Mock(
            return_value={'Account': '123456'})

        self.subscribe.s3 = mock.Mock()
        self.subscribe.s3.meta.region_name = 'us-east-1'
        policy_template = BytesIO(u'{"Statement": []}'.encode('latin-1'))
        self.subscribe.s3.get_object = mock.Mock(
            return_value={'Body': policy_template})
        self.subscribe.s3.head_bucket.return_value = {}

        self.subscribe.sns = mock.Mock()
        self.subscribe.sns.meta.region_name = 'us-east-1'
        self.subscribe.sns.list_topics = mock.Mock(
            return_value={'Topics': [{'TopicArn': ':test2'}]})
        self.subscribe.sns.create_topic = mock.Mock(
            return_value={'TopicArn': 'foo'})
        self.subscribe.sns.get_topic_attributes = mock.Mock(
            return_value={'Attributes': {'Policy': '{"Statement": []}'}})

    def test_clients_all_from_same_session(self):
        session = mock.Mock()
        subscribe_command = CloudTrailSubscribe(session)
        parsed_globals = mock.Mock(region=None, verify_ssl=None,
                              endpoint_url=None)
        subscribe_command.setup_services(None, parsed_globals)
        create_client_calls = session.create_client.call_args_list
        self.assertEqual(
            create_client_calls, [
                mock.call('sts', verify=None, region_name=None),
                mock.call('s3', verify=None, region_name=None),
                mock.call('sns', verify=None, region_name=None),
                mock.call('cloudtrail', verify=None, region_name=None),
            ]
        )

    def test_endpoint_url_is_only_used_for_cloudtrail(self):
        endpoint_url = 'https://mycloudtrail.awsamazon.com/'
        session = mock.Mock()
        subscribe_command = CloudTrailSubscribe(session)
        parsed_globals = mock.Mock(region=None, verify_ssl=None,
                              endpoint_url=endpoint_url)
        subscribe_command.setup_services(None, parsed_globals)
        create_client_calls = session.create_client.call_args_list
        self.assertEqual(
            create_client_calls, [
                mock.call('sts', verify=None, region_name=None),
                mock.call('s3', verify=None, region_name=None),
                mock.call('sns', verify=None, region_name=None),
                # Here we should inject the endpoint_url only for cloudtrail.
                mock.call('cloudtrail', verify=None, region_name=None,
                     endpoint_url=endpoint_url),
            ]
        )

    def test_s3_create(self):
        sts = self.subscribe.sts
        s3 = self.subscribe.s3
        s3.head_bucket.side_effect = ClientError(
            {'Error': {'Code': '404', 'Message': ''}}, 'HeadBucket')

        self.subscribe.setup_new_bucket('test', 'logs')

        sts.get_caller_identity.assert_called_with()

        s3.get_object.assert_called_with(
            Bucket='awscloudtrail-policy-us-east-1',
            Key='policy/S3/AWSCloudTrail-S3BucketPolicy-2014-12-17.json',
        )
        s3.create_bucket.assert_called_with(Bucket='test')
        s3.put_bucket_policy.assert_called_with(
            Bucket='test', Policy=u'{"Statement": []}'
        )

        self.assertFalse(s3.delete_bucket.called)

        args, kwargs = s3.create_bucket.call_args
        self.assertNotIn('create_bucket_configuration', kwargs)

    def test_s3_uses_regionalized_policy(self):
        s3 = self.subscribe.s3
        s3.head_bucket.side_effect = ClientError(
            {'Error': {'Code': '404', 'Message': ''}}, 'HeadBucket')

        self.subscribe.setup_new_bucket('test', 'logs')

        s3.get_object.assert_called_with(
            Bucket='awscloudtrail-policy-us-east-1', Key=mock.ANY)

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
        s3.put_bucket_policy = mock.Mock(side_effect=Exception('Error!'))

        with self.assertRaises(Exception):
            self.subscribe.setup_new_bucket('test', 'logs')

    def test_s3_get_policy_fail(self):
        self.subscribe.s3.get_object = mock.Mock(side_effect=Exception('Foo!'))

        with self.assertRaises(CloudTrailError) as cm:
            self.subscribe.setup_new_bucket('test', 'logs')

        # Exception should contain its custom message, the region
        # where there is an issue, and the original exception message.
        self.assertIn('us-east-1', str(cm.exception))
        self.assertIn('Foo!', str(cm.exception))

    def test_get_policy_read_timeout(self):
        response = {
            'Body': mock.Mock()
        }
        response['Body'].read.side_effect = Exception('Error!')
        self.subscribe.s3.get_object.return_value = response

        with self.assertRaises(CloudTrailError):
            self.subscribe.setup_new_bucket('test', 'logs')

    def test_sns_get_policy_fail(self):
        self.subscribe.s3.get_object = mock.Mock(side_effect=Exception('Error!'))

        with self.assertRaises(Exception):
            self.subscribe.setup_new_bucket('test', 'logs')

    def test_sns_create(self):
        s3 = self.subscribe.s3
        sns = self.subscribe.sns

        self.subscribe.setup_new_topic('test')

        s3.get_object.assert_called_with(
            Bucket='awscloudtrail-policy-us-east-1',
            Key='policy/SNS/AWSCloudTrail-SnsTopicPolicy-2014-12-17.json',
        )
        sns.list_topics.assert_called_with()
        sns.create_topic.assert_called_with(Name='test')
        sns.set_topic_attributes.assert_called_with(
            AttributeName='Policy',
            AttributeValue='{"Statement": []}',
            TopicArn='foo',
        )

        self.assertFalse(sns.delete_topic.called)

    def test_sns_uses_regionalized_policy(self):
        s3 = self.subscribe.s3

        self.subscribe.setup_new_topic('test')

        s3.get_object.assert_called_with(
            Bucket='awscloudtrail-policy-us-east-1', Key=mock.ANY)

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
          TopicArn=mock.ANY, AttributeName='Policy', AttributeValue=policy)

    def test_sns_create_already_exists(self):
        with self.assertRaises(Exception):
            self.subscribe.setup_new_topic('test2')

    def test_cloudtrail_new_call_format(self):
        self.subscribe.cloudtrail = mock.Mock()
        self.subscribe.cloudtrail.create_trail = mock.Mock(return_value={})
        self.subscribe.cloudtrail.describe_trail = mock.Mock(return_value={})

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
