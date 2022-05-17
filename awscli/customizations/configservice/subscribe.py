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
import json
import sys

from awscli.customizations.commands import BasicCommand
from awscli.customizations.utils import s3_bucket_exists
from awscli.customizations.s3.utils import find_bucket_key


S3_BUCKET = {'name': 's3-bucket', 'required': True,
             'help_text': ('The S3 bucket that the AWS Config delivery channel'
                           ' will use. If the bucket does not exist, it will '
                           'be automatically created. The value for this '
                           'argument should follow the form '
                           'bucket/prefix. Note that the prefix is optional.')}

SNS_TOPIC = {'name': 'sns-topic', 'required': True,
             'help_text': ('The SNS topic that the AWS Config delivery channel'
                           ' will use. If the SNS topic does not exist, it '
                           'will be automatically created. Value for this '
                           'should be a valid SNS topic name or the ARN of an '
                           'existing SNS topic.')}

IAM_ROLE = {'name': 'iam-role', 'required': True,
            'help_text': ('The IAM role that the AWS Config configuration '
                          'recorder will use to record current resource '
                          'configurations. Value for this should be the '
                          'ARN of the desired IAM role.')}


def register_subscribe(cli):
    cli.register('building-command-table.configservice', add_subscribe)


def add_subscribe(command_table, session, **kwargs):
    command_table['subscribe'] = SubscribeCommand(session)


class SubscribeCommand(BasicCommand):
    NAME = 'subscribe'
    DESCRIPTION = ('Subscribes user to AWS Config by creating an AWS Config '
                   'delivery channel and configuration recorder to track '
                   'AWS resource configurations. The names of the default '
                   'channel and configuration recorder will be default.')
    ARG_TABLE = [S3_BUCKET, SNS_TOPIC, IAM_ROLE]

    def __init__(self, session):
        self._s3_client = None
        self._sns_client = None
        self._config_client = None
        super(SubscribeCommand, self).__init__(session)

    def _run_main(self, parsed_args, parsed_globals):
        # Setup the necessary all of the necessary clients.
        self._setup_clients(parsed_globals)

        # Prepare a s3 bucket for use.
        s3_bucket_helper = S3BucketHelper(self._s3_client)
        bucket, prefix = s3_bucket_helper.prepare_bucket(parsed_args.s3_bucket)

        # Prepare a sns topic for use.
        sns_topic_helper = SNSTopicHelper(self._sns_client)
        sns_topic_arn = sns_topic_helper.prepare_topic(parsed_args.sns_topic)

        name = 'default'

        # Create a configuration recorder.
        self._config_client.put_configuration_recorder(
            ConfigurationRecorder={
                'name': name,
                'roleARN': parsed_args.iam_role
            }
        )

        # Create a delivery channel.
        delivery_channel = {
            'name': name,
            's3BucketName': bucket,
            'snsTopicARN': sns_topic_arn
        }

        if prefix:
            delivery_channel['s3KeyPrefix'] = prefix

        self._config_client.put_delivery_channel(
            DeliveryChannel=delivery_channel)

        # Start the configuration recorder.
        self._config_client.start_configuration_recorder(
            ConfigurationRecorderName=name
        )

        # Describe the configuration recorders
        sys.stdout.write('Subscribe succeeded:\n\n')
        sys.stdout.write('Configuration Recorders: ')
        response = self._config_client.describe_configuration_recorders()
        sys.stdout.write(
            json.dumps(response['ConfigurationRecorders'], indent=4))
        sys.stdout.write('\n\n')

        # Describe the delivery channels
        sys.stdout.write('Delivery Channels: ')
        response = self._config_client.describe_delivery_channels()
        sys.stdout.write(json.dumps(response['DeliveryChannels'], indent=4))
        sys.stdout.write('\n')

        return 0

    def _setup_clients(self, parsed_globals):
        client_args = {
            'verify': parsed_globals.verify_ssl,
            'region_name': parsed_globals.region
        }
        self._s3_client = self._session.create_client('s3', **client_args)
        self._sns_client = self._session.create_client('sns', **client_args)
        # Use the specified endpoint only for config related commands.
        client_args['endpoint_url'] = parsed_globals.endpoint_url
        self._config_client = self._session.create_client('config',
                                                          **client_args)


class S3BucketHelper(object):
    def __init__(self, s3_client):
        self._s3_client = s3_client

    def prepare_bucket(self, s3_path):
        bucket, key = find_bucket_key(s3_path)
        bucket_exists = self._check_bucket_exists(bucket)
        if not bucket_exists:
            self._create_bucket(bucket)
            sys.stdout.write('Using new S3 bucket: %s\n' % bucket)
        else:
            sys.stdout.write('Using existing S3 bucket: %s\n' % bucket)
        return bucket, key

    def _check_bucket_exists(self, bucket):
        return s3_bucket_exists(self._s3_client, bucket)

    def _create_bucket(self, bucket):
        region_name = self._s3_client.meta.region_name
        params = {
            'Bucket': bucket
        }
        bucket_config = {'LocationConstraint': region_name}
        if region_name != 'us-east-1':
            params['CreateBucketConfiguration'] = bucket_config
        self._s3_client.create_bucket(**params)


class SNSTopicHelper(object):
    def __init__(self, sns_client):
        self._sns_client = sns_client

    def prepare_topic(self, sns_topic):
        sns_topic_arn = sns_topic
        # Create the topic if a name is given.
        if not self._check_is_arn(sns_topic):
            response = self._sns_client.create_topic(Name=sns_topic)
            sns_topic_arn = response['TopicArn']
            sys.stdout.write('Using new SNS topic: %s\n' % sns_topic_arn)
        else:
            sys.stdout.write('Using existing SNS topic: %s\n' % sns_topic_arn)
        return sns_topic_arn

    def _check_is_arn(self, sns_topic):
        # The name of topic cannot contain a colon only arns have colons.
        return ':' in sns_topic
