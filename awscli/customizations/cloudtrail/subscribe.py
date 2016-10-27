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
import logging
import sys

from .utils import get_account_id
from awscli.customizations.commands import BasicCommand
from awscli.customizations.utils import s3_bucket_exists
from botocore.exceptions import ClientError


LOG = logging.getLogger(__name__)
S3_POLICY_TEMPLATE = 'policy/S3/AWSCloudTrail-S3BucketPolicy-2014-12-17.json'
SNS_POLICY_TEMPLATE = 'policy/SNS/AWSCloudTrail-SnsTopicPolicy-2014-12-17.json'


class CloudTrailError(Exception):
    pass


class CloudTrailSubscribe(BasicCommand):
    """
    Subscribe/update a user account to CloudTrail, creating the required S3 bucket,
    the optional SNS topic, and starting the CloudTrail monitoring and logging.
    """
    NAME = 'create-subscription'
    DESCRIPTION = ('Creates and configures the AWS resources necessary to use'
                   ' CloudTrail, creates a trail using those resources, and '
                   'turns on logging.')
    SYNOPSIS = ('aws cloudtrail create-subscription'
                ' (--s3-use-bucket|--s3-new-bucket) bucket-name'
                ' [--sns-new-topic topic-name]\n')

    ARG_TABLE = [
        {'name': 'name', 'required': True, 'help_text': 'Cloudtrail name'},
        {'name': 's3-new-bucket',
         'help_text': 'Create a new S3 bucket with this name'},
        {'name': 's3-use-bucket',
         'help_text': 'Use an existing S3 bucket with this name'},
        {'name': 's3-prefix', 'help_text': 'S3 object prefix'},
        {'name': 'sns-new-topic',
         'help_text': 'Create a new SNS topic with this name'},
        {'name': 'include-global-service-events',
         'help_text': 'Whether to include global service events'},
        {'name': 's3-custom-policy',
         'help_text': 'Custom S3 policy template or URL'},
        {'name': 'sns-custom-policy',
         'help_text': 'Custom SNS policy template or URL'}
    ]

    UPDATE = False

    def _run_main(self, args, parsed_globals):
        self.setup_services(args, parsed_globals)
        # Run the command and report success
        self._call(args, parsed_globals)

        return 0

    def setup_services(self, args, parsed_globals):
        client_args = {
            'region_name': None,
            'verify': None
        }
        if parsed_globals.region is not None:
            client_args['region_name'] = parsed_globals.region
        if parsed_globals.verify_ssl is not None:
            client_args['verify'] = parsed_globals.verify_ssl

        # Initialize services
        LOG.debug('Initializing S3, SNS and CloudTrail...')
        self.sts = self._session.create_client('sts', **client_args)
        self.s3 = self._session.create_client('s3', **client_args)
        self.sns = self._session.create_client('sns', **client_args)
        self.region_name = self.s3.meta.region_name

        # If the endpoint is specified, it is designated for the cloudtrail
        # service. Not all of the other services will use it.
        if parsed_globals.endpoint_url is not None:
            client_args['endpoint_url'] = parsed_globals.endpoint_url
        self.cloudtrail = self._session.create_client('cloudtrail', **client_args)

    def _call(self, options, parsed_globals):
        """
        Run the command. Calls various services based on input options and
        outputs the final CloudTrail configuration.
        """
        gse = options.include_global_service_events
        if gse:
            if gse.lower() == 'true':
                gse = True
            elif gse.lower() == 'false':
                gse = False
            else:
                raise ValueError('You must pass either true or false to'
                                 ' --include-global-service-events.')

        bucket = options.s3_use_bucket

        if options.s3_new_bucket:
            bucket = options.s3_new_bucket

            if self.UPDATE and options.s3_prefix is None:
                # Prefix was not passed and this is updating the S3 bucket,
                # so let's find the existing prefix and use that if possible
                res = self.cloudtrail.describe_trails(
                    trailNameList=[options.name])
                trail_info = res['trailList'][0]

                if 'S3KeyPrefix' in trail_info:
                    LOG.debug('Setting S3 prefix to {0}'.format(
                        trail_info['S3KeyPrefix']))
                    options.s3_prefix = trail_info['S3KeyPrefix']

            self.setup_new_bucket(bucket, options.s3_prefix,
                                  options.s3_custom_policy)
        elif not bucket and not self.UPDATE:
            # No bucket was passed for creation.
            raise ValueError('You must pass either --s3-use-bucket or'
                             ' --s3-new-bucket to create.')

        if options.sns_new_topic:
            try:
                topic_result = self.setup_new_topic(options.sns_new_topic,
                                                    options.sns_custom_policy)
            except Exception:
                # Roll back any S3 bucket creation
                if options.s3_new_bucket:
                    self.s3.delete_bucket(Bucket=options.s3_new_bucket)
                raise

        try:
            cloudtrail_config = self.upsert_cloudtrail_config(
                options.name,
                bucket,
                options.s3_prefix,
                options.sns_new_topic,
                gse
            )
        except Exception:
            # Roll back any S3 bucket / SNS topic creations
            if options.s3_new_bucket:
                self.s3.delete_bucket(Bucket=options.s3_new_bucket)
            if options.sns_new_topic:
                self.sns.delete_topic(TopicArn=topic_result['TopicArn'])
            raise

        sys.stdout.write('CloudTrail configuration:\n{config}\n'.format(
            config=json.dumps(cloudtrail_config, indent=2)))

        if not self.UPDATE:
            # If the configure call command above completes then this should
            # have a really high chance of also completing
            self.start_cloudtrail(options.name)

            sys.stdout.write(
                'Logs will be delivered to {bucket}:{prefix}\n'.format(
                    bucket=bucket, prefix=options.s3_prefix or ''))

    def _get_policy(self, key_name):
        try:
            data = self.s3.get_object(
                Bucket='awscloudtrail-policy-' + self.region_name,
                Key=key_name)
            return data['Body'].read().decode('utf-8')
        except Exception as e:
            raise CloudTrailError(
                'Unable to get regional policy template for'
                ' region %s: %s. Error: %s', self.region_name, key_name, e)

    def setup_new_bucket(self, bucket, prefix, custom_policy=None):
        """
        Creates a new S3 bucket with an appropriate policy to let CloudTrail
        write to the prefix path.
        """
        sys.stdout.write(
            'Setting up new S3 bucket {bucket}...\n'.format(bucket=bucket))

        account_id = get_account_id(self.sts)

        # Clean up the prefix - it requires a trailing slash if set
        if prefix and not prefix.endswith('/'):
            prefix += '/'

        # Fetch policy data from S3 or a custom URL
        if custom_policy is not None:
            policy = custom_policy
        else:
            policy = self._get_policy(S3_POLICY_TEMPLATE)

        policy = policy.replace('<BucketName>', bucket)\
                       .replace('<CustomerAccountID>', account_id)

        if '<Prefix>/' in policy:
            policy = policy.replace('<Prefix>/', prefix or '')
        else:
            policy = policy.replace('<Prefix>', prefix or '')

        LOG.debug('Bucket policy:\n{0}'.format(policy))
        bucket_exists = s3_bucket_exists(self.s3, bucket)
        if bucket_exists:
            raise Exception('Bucket {bucket} already exists.'.format(
                bucket=bucket))

        # If we are not using the us-east-1 region, then we must set
        # a location constraint on the new bucket.
        params = {'Bucket': bucket}
        if self.region_name != 'us-east-1':
            bucket_config = {'LocationConstraint': self.region_name}
            params['CreateBucketConfiguration'] = bucket_config

        data = self.s3.create_bucket(**params)

        try:
            self.s3.put_bucket_policy(Bucket=bucket, Policy=policy)
        except ClientError:
            # Roll back bucket creation.
            self.s3.delete_bucket(Bucket=bucket)
            raise

        return data

    def setup_new_topic(self, topic, custom_policy=None):
        """
        Creates a new SNS topic with an appropriate policy to let CloudTrail
        post messages to the topic.
        """
        sys.stdout.write(
            'Setting up new SNS topic {topic}...\n'.format(topic=topic))

        account_id = get_account_id(self.sts)

        # Make sure topic doesn't already exist
        # Warn but do not fail if ListTopics permissions
        # are missing from the IAM role?
        try:
            topics = self.sns.list_topics()['Topics']
        except Exception:
            topics = []
            LOG.warn('Unable to list topics, continuing...')

        if [t for t in topics if t['TopicArn'].split(':')[-1] == topic]:
            raise Exception('Topic {topic} already exists.'.format(
                topic=topic))

        region = self.sns.meta.region_name

        # Get the SNS topic policy information to allow CloudTrail
        # write-access.
        if custom_policy is not None:
            policy = custom_policy
        else:
            policy = self._get_policy(SNS_POLICY_TEMPLATE)

        policy = policy.replace('<Region>', region)\
                       .replace('<SNSTopicOwnerAccountId>', account_id)\
                       .replace('<SNSTopicName>', topic)

        topic_result = self.sns.create_topic(Name=topic)

        try:
            # Merge any existing topic policy with our new policy statements
            topic_attr = self.sns.get_topic_attributes(
                TopicArn=topic_result['TopicArn'])

            policy = self.merge_sns_policy(topic_attr['Attributes']['Policy'],
                                           policy)

            LOG.debug('Topic policy:\n{0}'.format(policy))

            # Set the topic policy
            self.sns.set_topic_attributes(TopicArn=topic_result['TopicArn'],
                                          AttributeName='Policy',
                                          AttributeValue=policy)
        except Exception:
            # Roll back topic creation
            self.sns.delete_topic(TopicArn=topic_result['TopicArn'])
            raise

        return topic_result

    def merge_sns_policy(self, left, right):
        """
        Merge two SNS topic policy documents. The id information from
        ``left`` is used in the final document, and the statements
        from ``right`` are merged into ``left``.

        http://docs.aws.amazon.com/sns/latest/dg/BasicStructure.html

        :type left: string
        :param left: First policy JSON document
        :type right: string
        :param right: Second policy JSON document
        :rtype: string
        :return: Merged policy JSON
        """
        left_parsed = json.loads(left)
        right_parsed = json.loads(right)
        left_parsed['Statement'] += right_parsed['Statement']
        return json.dumps(left_parsed)

    def upsert_cloudtrail_config(self, name, bucket, prefix, topic, gse):
        """
        Either create or update the CloudTrail configuration depending on
        whether this command is a create or update command.
        """
        sys.stdout.write('Creating/updating CloudTrail configuration...\n')
        config = {
            'Name': name
        }
        if bucket is not None:
            config['S3BucketName'] = bucket
        if prefix is not None:
            config['S3KeyPrefix'] = prefix
        if topic is not None:
            config['SnsTopicName'] = topic
        if gse is not None:
            config['IncludeGlobalServiceEvents'] = gse
        if not self.UPDATE:
            self.cloudtrail.create_trail(**config)
        else:
            self.cloudtrail.update_trail(**config)
        return self.cloudtrail.describe_trails()

    def start_cloudtrail(self, name):
        """
        Start the CloudTrail service, which begins logging.
        """
        sys.stdout.write('Starting CloudTrail service...\n')
        return self.cloudtrail.start_logging(Name=name)


class CloudTrailUpdate(CloudTrailSubscribe):
    """
    Like subscribe above, but the update version of the command.
    """
    NAME = 'update-subscription'
    UPDATE = True

    DESCRIPTION = ('Updates any of the trail configuration settings, and'
                   ' creates and configures any new AWS resources specified.')

    SYNOPSIS = ('aws cloudtrail update-subscription'
                ' [(--s3-use-bucket|--s3-new-bucket) bucket-name]'
                ' [--sns-new-topic topic-name]\n')
