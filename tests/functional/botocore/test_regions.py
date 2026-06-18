# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import pytest

from botocore.client import ClientEndpointBridge
from botocore.exceptions import NoRegionError
from tests import BaseSessionTest, ClientHTTPStubber, mock

# NOTE: sqs endpoint updated to be the CN in the SSL cert because
# a bug in python2.6 prevents subjectAltNames from being parsed
# and subsequently being used in cert validation.
# Same thing is needed for rds.
KNOWN_REGIONS = {
    'ap-northeast-1': {
        'apigateway': 'apigateway.ap-northeast-1.amazonaws.com',
        'appstream': 'appstream.ap-northeast-1.amazonaws.com',
        'autoscaling': 'autoscaling.ap-northeast-1.amazonaws.com',
        'cloudformation': 'cloudformation.ap-northeast-1.amazonaws.com',
        'cloudhsm': 'cloudhsm.ap-northeast-1.amazonaws.com',
        'cloudsearch': 'cloudsearch.ap-northeast-1.amazonaws.com',
        'cloudtrail': 'cloudtrail.ap-northeast-1.amazonaws.com',
        'codedeploy': 'codedeploy.ap-northeast-1.amazonaws.com',
        'cognito-identity': 'cognito-identity.ap-northeast-1.amazonaws.com',
        'cognito-sync': 'cognito-sync.ap-northeast-1.amazonaws.com',
        'config': 'config.ap-northeast-1.amazonaws.com',
        'datapipeline': 'datapipeline.ap-northeast-1.amazonaws.com',
        'directconnect': 'directconnect.ap-northeast-1.amazonaws.com',
        'ds': 'ds.ap-northeast-1.amazonaws.com',
        'dynamodb': 'dynamodb.ap-northeast-1.amazonaws.com',
        'ec2': 'ec2.ap-northeast-1.amazonaws.com',
        'ecs': 'ecs.ap-northeast-1.amazonaws.com',
        'elasticache': 'elasticache.ap-northeast-1.amazonaws.com',
        'elasticbeanstalk': 'elasticbeanstalk.ap-northeast-1.amazonaws.com',
        'elasticloadbalancing': 'elasticloadbalancing.ap-northeast-1.amazonaws.com',
        'elasticmapreduce': 'elasticmapreduce.ap-northeast-1.amazonaws.com',
        'glacier': 'glacier.ap-northeast-1.amazonaws.com',
        'iot': 'iot.ap-northeast-1.amazonaws.com',
        'kinesis': 'kinesis.ap-northeast-1.amazonaws.com',
        'kms': 'kms.ap-northeast-1.amazonaws.com',
        'lambda': 'lambda.ap-northeast-1.amazonaws.com',
        'logs': 'logs.ap-northeast-1.amazonaws.com',
        'monitoring': 'monitoring.ap-northeast-1.amazonaws.com',
        'rds': 'rds.ap-northeast-1.amazonaws.com',
        'redshift': 'redshift.ap-northeast-1.amazonaws.com',
        's3': 's3.ap-northeast-1.amazonaws.com',
        'sdb': 'sdb.ap-northeast-1.amazonaws.com',
        'sns': 'sns.ap-northeast-1.amazonaws.com',
        'sqs': 'sqs.ap-northeast-1.amazonaws.com',
        'storagegateway': 'storagegateway.ap-northeast-1.amazonaws.com',
        'streams.dynamodb': 'streams.dynamodb.ap-northeast-1.amazonaws.com',
        'sts': 'sts.ap-northeast-1.amazonaws.com',
        'swf': 'swf.ap-northeast-1.amazonaws.com',
        'workspaces': 'workspaces.ap-northeast-1.amazonaws.com',
    },
    'ap-southeast-1': {
        'autoscaling': 'autoscaling.ap-southeast-1.amazonaws.com',
        'cloudformation': 'cloudformation.ap-southeast-1.amazonaws.com',
        'cloudhsm': 'cloudhsm.ap-southeast-1.amazonaws.com',
        'cloudsearch': 'cloudsearch.ap-southeast-1.amazonaws.com',
        'cloudtrail': 'cloudtrail.ap-southeast-1.amazonaws.com',
        'config': 'config.ap-southeast-1.amazonaws.com',
        'directconnect': 'directconnect.ap-southeast-1.amazonaws.com',
        'ds': 'ds.ap-southeast-1.amazonaws.com',
        'dynamodb': 'dynamodb.ap-southeast-1.amazonaws.com',
        'ec2': 'ec2.ap-southeast-1.amazonaws.com',
        'elasticache': 'elasticache.ap-southeast-1.amazonaws.com',
        'elasticbeanstalk': 'elasticbeanstalk.ap-southeast-1.amazonaws.com',
        'elasticloadbalancing': 'elasticloadbalancing.ap-southeast-1.amazonaws.com',
        'elasticmapreduce': 'elasticmapreduce.ap-southeast-1.amazonaws.com',
        'kinesis': 'kinesis.ap-southeast-1.amazonaws.com',
        'kms': 'kms.ap-southeast-1.amazonaws.com',
        'logs': 'logs.ap-southeast-1.amazonaws.com',
        'monitoring': 'monitoring.ap-southeast-1.amazonaws.com',
        'rds': 'rds.ap-southeast-1.amazonaws.com',
        'redshift': 'redshift.ap-southeast-1.amazonaws.com',
        's3': 's3.ap-southeast-1.amazonaws.com',
        'sdb': 'sdb.ap-southeast-1.amazonaws.com',
        'sns': 'sns.ap-southeast-1.amazonaws.com',
        'sqs': 'sqs.ap-southeast-1.amazonaws.com',
        'storagegateway': 'storagegateway.ap-southeast-1.amazonaws.com',
        'streams.dynamodb': 'streams.dynamodb.ap-southeast-1.amazonaws.com',
        'sts': 'sts.ap-southeast-1.amazonaws.com',
        'swf': 'swf.ap-southeast-1.amazonaws.com',
        'workspaces': 'workspaces.ap-southeast-1.amazonaws.com',
    },
    'ap-southeast-2': {
        'autoscaling': 'autoscaling.ap-southeast-2.amazonaws.com',
        'cloudformation': 'cloudformation.ap-southeast-2.amazonaws.com',
        'cloudhsm': 'cloudhsm.ap-southeast-2.amazonaws.com',
        'cloudsearch': 'cloudsearch.ap-southeast-2.amazonaws.com',
        'cloudtrail': 'cloudtrail.ap-southeast-2.amazonaws.com',
        'codedeploy': 'codedeploy.ap-southeast-2.amazonaws.com',
        'config': 'config.ap-southeast-2.amazonaws.com',
        'datapipeline': 'datapipeline.ap-southeast-2.amazonaws.com',
        'directconnect': 'directconnect.ap-southeast-2.amazonaws.com',
        'ds': 'ds.ap-southeast-2.amazonaws.com',
        'dynamodb': 'dynamodb.ap-southeast-2.amazonaws.com',
        'ec2': 'ec2.ap-southeast-2.amazonaws.com',
        'ecs': 'ecs.ap-southeast-2.amazonaws.com',
        'elasticache': 'elasticache.ap-southeast-2.amazonaws.com',
        'elasticbeanstalk': 'elasticbeanstalk.ap-southeast-2.amazonaws.com',
        'elasticloadbalancing': 'elasticloadbalancing.ap-southeast-2.amazonaws.com',
        'elasticmapreduce': 'elasticmapreduce.ap-southeast-2.amazonaws.com',
        'glacier': 'glacier.ap-southeast-2.amazonaws.com',
        'kinesis': 'kinesis.ap-southeast-2.amazonaws.com',
        'kms': 'kms.ap-southeast-2.amazonaws.com',
        'logs': 'logs.ap-southeast-2.amazonaws.com',
        'monitoring': 'monitoring.ap-southeast-2.amazonaws.com',
        'rds': 'rds.ap-southeast-2.amazonaws.com',
        'redshift': 'redshift.ap-southeast-2.amazonaws.com',
        's3': 's3.ap-southeast-2.amazonaws.com',
        'sdb': 'sdb.ap-southeast-2.amazonaws.com',
        'sns': 'sns.ap-southeast-2.amazonaws.com',
        'sqs': 'sqs.ap-southeast-2.amazonaws.com',
        'storagegateway': 'storagegateway.ap-southeast-2.amazonaws.com',
        'streams.dynamodb': 'streams.dynamodb.ap-southeast-2.amazonaws.com',
        'sts': 'sts.ap-southeast-2.amazonaws.com',
        'swf': 'swf.ap-southeast-2.amazonaws.com',
        'workspaces': 'workspaces.ap-southeast-2.amazonaws.com',
    },
    'aws-us-gov-global': {'iam': 'iam.us-gov.amazonaws.com'},
    'cn-north-1': {
        'autoscaling': 'autoscaling.cn-north-1.amazonaws.com.cn',
        'cloudformation': 'cloudformation.cn-north-1.amazonaws.com.cn',
        'cloudtrail': 'cloudtrail.cn-north-1.amazonaws.com.cn',
        'directconnect': 'directconnect.cn-north-1.amazonaws.com.cn',
        'dynamodb': 'dynamodb.cn-north-1.amazonaws.com.cn',
        'ec2': 'ec2.cn-north-1.amazonaws.com.cn',
        'elasticache': 'elasticache.cn-north-1.amazonaws.com.cn',
        'elasticbeanstalk': 'elasticbeanstalk.cn-north-1.amazonaws.com.cn',
        'elasticloadbalancing': 'elasticloadbalancing.cn-north-1.amazonaws.com.cn',
        'elasticmapreduce': 'elasticmapreduce.cn-north-1.amazonaws.com.cn',
        'glacier': 'glacier.cn-north-1.amazonaws.com.cn',
        'iam': 'iam.cn-north-1.amazonaws.com.cn',
        'kinesis': 'kinesis.cn-north-1.amazonaws.com.cn',
        'monitoring': 'monitoring.cn-north-1.amazonaws.com.cn',
        'rds': 'rds.cn-north-1.amazonaws.com.cn',
        's3': 's3.cn-north-1.amazonaws.com.cn',
        'sns': 'sns.cn-north-1.amazonaws.com.cn',
        'sqs': 'sqs.cn-north-1.amazonaws.com.cn',
        'storagegateway': 'storagegateway.cn-north-1.amazonaws.com.cn',
        'streams.dynamodb': 'streams.dynamodb.cn-north-1.amazonaws.com.cn',
        'sts': 'sts.cn-north-1.amazonaws.com.cn',
        'swf': 'swf.cn-north-1.amazonaws.com.cn',
    },
    'eu-central-1': {
        'autoscaling': 'autoscaling.eu-central-1.amazonaws.com',
        'cloudformation': 'cloudformation.eu-central-1.amazonaws.com',
        'cloudhsm': 'cloudhsm.eu-central-1.amazonaws.com',
        'cloudsearch': 'cloudsearch.eu-central-1.amazonaws.com',
        'cloudtrail': 'cloudtrail.eu-central-1.amazonaws.com',
        'codedeploy': 'codedeploy.eu-central-1.amazonaws.com',
        'config': 'config.eu-central-1.amazonaws.com',
        'directconnect': 'directconnect.eu-central-1.amazonaws.com',
        'dynamodb': 'dynamodb.eu-central-1.amazonaws.com',
        'ec2': 'ec2.eu-central-1.amazonaws.com',
        'elasticache': 'elasticache.eu-central-1.amazonaws.com',
        'elasticbeanstalk': 'elasticbeanstalk.eu-central-1.amazonaws.com',
        'elasticloadbalancing': 'elasticloadbalancing.eu-central-1.amazonaws.com',
        'elasticmapreduce': 'elasticmapreduce.eu-central-1.amazonaws.com',
        'glacier': 'glacier.eu-central-1.amazonaws.com',
        'kinesis': 'kinesis.eu-central-1.amazonaws.com',
        'kms': 'kms.eu-central-1.amazonaws.com',
        'logs': 'logs.eu-central-1.amazonaws.com',
        'monitoring': 'monitoring.eu-central-1.amazonaws.com',
        'rds': 'rds.eu-central-1.amazonaws.com',
        'redshift': 'redshift.eu-central-1.amazonaws.com',
        's3': 's3.eu-central-1.amazonaws.com',
        'sns': 'sns.eu-central-1.amazonaws.com',
        'sqs': 'sqs.eu-central-1.amazonaws.com',
        'storagegateway': 'storagegateway.eu-central-1.amazonaws.com',
        'streams.dynamodb': 'streams.dynamodb.eu-central-1.amazonaws.com',
        'sts': 'sts.eu-central-1.amazonaws.com',
        'swf': 'swf.eu-central-1.amazonaws.com',
    },
    'eu-west-1': {
        'apigateway': 'apigateway.eu-west-1.amazonaws.com',
        'autoscaling': 'autoscaling.eu-west-1.amazonaws.com',
        'cloudformation': 'cloudformation.eu-west-1.amazonaws.com',
        'cloudhsm': 'cloudhsm.eu-west-1.amazonaws.com',
        'cloudsearch': 'cloudsearch.eu-west-1.amazonaws.com',
        'cloudtrail': 'cloudtrail.eu-west-1.amazonaws.com',
        'codedeploy': 'codedeploy.eu-west-1.amazonaws.com',
        'cognito-identity': 'cognito-identity.eu-west-1.amazonaws.com',
        'cognito-sync': 'cognito-sync.eu-west-1.amazonaws.com',
        'config': 'config.eu-west-1.amazonaws.com',
        'datapipeline': 'datapipeline.eu-west-1.amazonaws.com',
        'directconnect': 'directconnect.eu-west-1.amazonaws.com',
        'ds': 'ds.eu-west-1.amazonaws.com',
        'dynamodb': 'dynamodb.eu-west-1.amazonaws.com',
        'ec2': 'ec2.eu-west-1.amazonaws.com',
        'ecs': 'ecs.eu-west-1.amazonaws.com',
        'elasticache': 'elasticache.eu-west-1.amazonaws.com',
        'elasticbeanstalk': 'elasticbeanstalk.eu-west-1.amazonaws.com',
        'elasticloadbalancing': 'elasticloadbalancing.eu-west-1.amazonaws.com',
        'elasticmapreduce': 'elasticmapreduce.eu-west-1.amazonaws.com',
        'email': 'email.eu-west-1.amazonaws.com',
        'glacier': 'glacier.eu-west-1.amazonaws.com',
        'iot': 'iot.eu-west-1.amazonaws.com',
        'kinesis': 'kinesis.eu-west-1.amazonaws.com',
        'kms': 'kms.eu-west-1.amazonaws.com',
        'lambda': 'lambda.eu-west-1.amazonaws.com',
        'logs': 'logs.eu-west-1.amazonaws.com',
        'machinelearning': 'machinelearning.eu-west-1.amazonaws.com',
        'monitoring': 'monitoring.eu-west-1.amazonaws.com',
        'rds': 'rds.eu-west-1.amazonaws.com',
        'redshift': 'redshift.eu-west-1.amazonaws.com',
        's3': 's3.eu-west-1.amazonaws.com',
        'sdb': 'sdb.eu-west-1.amazonaws.com',
        'sns': 'sns.eu-west-1.amazonaws.com',
        'sqs': 'sqs.eu-west-1.amazonaws.com',
        'ssm': 'ssm.eu-west-1.amazonaws.com',
        'storagegateway': 'storagegateway.eu-west-1.amazonaws.com',
        'streams.dynamodb': 'streams.dynamodb.eu-west-1.amazonaws.com',
        'sts': 'sts.eu-west-1.amazonaws.com',
        'swf': 'swf.eu-west-1.amazonaws.com',
        'workspaces': 'workspaces.eu-west-1.amazonaws.com',
    },
    'fips-us-gov-west-1': {'s3': 's3-fips.us-gov-west-1.amazonaws.com'},
    's3-external-1': {'s3': 's3-external-1.amazonaws.com'},
    'sa-east-1': {
        'autoscaling': 'autoscaling.sa-east-1.amazonaws.com',
        'cloudformation': 'cloudformation.sa-east-1.amazonaws.com',
        'cloudsearch': 'cloudsearch.sa-east-1.amazonaws.com',
        'cloudtrail': 'cloudtrail.sa-east-1.amazonaws.com',
        'config': 'config.sa-east-1.amazonaws.com',
        'directconnect': 'directconnect.sa-east-1.amazonaws.com',
        'dynamodb': 'dynamodb.sa-east-1.amazonaws.com',
        'ec2': 'ec2.sa-east-1.amazonaws.com',
        'elasticache': 'elasticache.sa-east-1.amazonaws.com',
        'elasticbeanstalk': 'elasticbeanstalk.sa-east-1.amazonaws.com',
        'elasticloadbalancing': 'elasticloadbalancing.sa-east-1.amazonaws.com',
        'elasticmapreduce': 'elasticmapreduce.sa-east-1.amazonaws.com',
        'kms': 'kms.sa-east-1.amazonaws.com',
        'monitoring': 'monitoring.sa-east-1.amazonaws.com',
        'rds': 'rds.sa-east-1.amazonaws.com',
        's3': 's3.sa-east-1.amazonaws.com',
        'sdb': 'sdb.sa-east-1.amazonaws.com',
        'sns': 'sns.sa-east-1.amazonaws.com',
        'sqs': 'sqs.sa-east-1.amazonaws.com',
        'storagegateway': 'storagegateway.sa-east-1.amazonaws.com',
        'streams.dynamodb': 'streams.dynamodb.sa-east-1.amazonaws.com',
        'sts': 'sts.sa-east-1.amazonaws.com',
        'swf': 'swf.sa-east-1.amazonaws.com',
    },
    'us-east-1': {
        'apigateway': 'apigateway.us-east-1.amazonaws.com',
        'appstream': 'appstream.us-east-1.amazonaws.com',
        'autoscaling': 'autoscaling.us-east-1.amazonaws.com',
        'cloudformation': 'cloudformation.us-east-1.amazonaws.com',
        'cloudfront': 'cloudfront.amazonaws.com',
        'cloudhsm': 'cloudhsm.us-east-1.amazonaws.com',
        'cloudsearch': 'cloudsearch.us-east-1.amazonaws.com',
        'cloudtrail': 'cloudtrail.us-east-1.amazonaws.com',
        'codecommit': 'codecommit.us-east-1.amazonaws.com',
        'codedeploy': 'codedeploy.us-east-1.amazonaws.com',
        'codepipeline': 'codepipeline.us-east-1.amazonaws.com',
        'cognito-identity': 'cognito-identity.us-east-1.amazonaws.com',
        'cognito-sync': 'cognito-sync.us-east-1.amazonaws.com',
        'config': 'config.us-east-1.amazonaws.com',
        'datapipeline': 'datapipeline.us-east-1.amazonaws.com',
        'directconnect': 'directconnect.us-east-1.amazonaws.com',
        'ds': 'ds.us-east-1.amazonaws.com',
        'dynamodb': 'dynamodb.us-east-1.amazonaws.com',
        'ec2': 'ec2.us-east-1.amazonaws.com',
        'ecs': 'ecs.us-east-1.amazonaws.com',
        'elasticache': 'elasticache.us-east-1.amazonaws.com',
        'elasticbeanstalk': 'elasticbeanstalk.us-east-1.amazonaws.com',
        'elasticloadbalancing': 'elasticloadbalancing.us-east-1.amazonaws.com',
        'elasticmapreduce': 'elasticmapreduce.us-east-1.amazonaws.com',
        'email': 'email.us-east-1.amazonaws.com',
        'glacier': 'glacier.us-east-1.amazonaws.com',
        'iam': 'iam.amazonaws.com',
        'importexport': 'importexport.amazonaws.com',
        'iot': 'iot.us-east-1.amazonaws.com',
        'kinesis': 'kinesis.us-east-1.amazonaws.com',
        'kms': 'kms.us-east-1.amazonaws.com',
        'lambda': 'lambda.us-east-1.amazonaws.com',
        'logs': 'logs.us-east-1.amazonaws.com',
        'machinelearning': 'machinelearning.us-east-1.amazonaws.com',
        'mobileanalytics': 'mobileanalytics.us-east-1.amazonaws.com',
        'monitoring': 'monitoring.us-east-1.amazonaws.com',
        'rds': 'rds.us-east-1.amazonaws.com',
        'redshift': 'redshift.us-east-1.amazonaws.com',
        'route53': 'route53.amazonaws.com',
        'route53domains': 'route53domains.us-east-1.amazonaws.com',
        's3': 's3.us-east-1.amazonaws.com',
        'sdb': 'sdb.amazonaws.com',
        'sns': 'sns.us-east-1.amazonaws.com',
        'sqs': 'sqs.us-east-1.amazonaws.com',
        'ssm': 'ssm.us-east-1.amazonaws.com',
        'storagegateway': 'storagegateway.us-east-1.amazonaws.com',
        'streams.dynamodb': 'streams.dynamodb.us-east-1.amazonaws.com',
        'sts': 'sts.us-east-1.amazonaws.com',
        'support': 'support.us-east-1.amazonaws.com',
        'swf': 'swf.us-east-1.amazonaws.com',
        'workspaces': 'workspaces.us-east-1.amazonaws.com',
        'waf': 'waf.amazonaws.com',
    },
    'us-gov-west-1': {
        'autoscaling': 'autoscaling.us-gov-west-1.amazonaws.com',
        'cloudformation': 'cloudformation.us-gov-west-1.amazonaws.com',
        'cloudhsm': 'cloudhsm.us-gov-west-1.amazonaws.com',
        'cloudtrail': 'cloudtrail.us-gov-west-1.amazonaws.com',
        'dynamodb': 'dynamodb.us-gov-west-1.amazonaws.com',
        'ec2': 'ec2.us-gov-west-1.amazonaws.com',
        'elasticache': 'elasticache.us-gov-west-1.amazonaws.com',
        'elasticloadbalancing': 'elasticloadbalancing.us-gov-west-1.amazonaws.com',
        'elasticmapreduce': 'elasticmapreduce.us-gov-west-1.amazonaws.com',
        'glacier': 'glacier.us-gov-west-1.amazonaws.com',
        'iam': 'iam.us-gov.amazonaws.com',
        'kms': 'kms.us-gov-west-1.amazonaws.com',
        'monitoring': 'monitoring.us-gov-west-1.amazonaws.com',
        'rds': 'rds.us-gov-west-1.amazonaws.com',
        'redshift': 'redshift.us-gov-west-1.amazonaws.com',
        's3': 's3.us-gov-west-1.amazonaws.com',
        'sns': 'sns.us-gov-west-1.amazonaws.com',
        'sqs': 'sqs.us-gov-west-1.amazonaws.com',
        'sts': 'sts.us-gov-west-1.amazonaws.com',
        'swf': 'swf.us-gov-west-1.amazonaws.com',
    },
    'us-west-1': {
        'autoscaling': 'autoscaling.us-west-1.amazonaws.com',
        'cloudformation': 'cloudformation.us-west-1.amazonaws.com',
        'cloudsearch': 'cloudsearch.us-west-1.amazonaws.com',
        'cloudtrail': 'cloudtrail.us-west-1.amazonaws.com',
        'config': 'config.us-west-1.amazonaws.com',
        'directconnect': 'directconnect.us-west-1.amazonaws.com',
        'dynamodb': 'dynamodb.us-west-1.amazonaws.com',
        'ec2': 'ec2.us-west-1.amazonaws.com',
        'ecs': 'ecs.us-west-1.amazonaws.com',
        'elasticache': 'elasticache.us-west-1.amazonaws.com',
        'elasticbeanstalk': 'elasticbeanstalk.us-west-1.amazonaws.com',
        'elasticloadbalancing': 'elasticloadbalancing.us-west-1.amazonaws.com',
        'elasticmapreduce': 'elasticmapreduce.us-west-1.amazonaws.com',
        'glacier': 'glacier.us-west-1.amazonaws.com',
        'kinesis': 'kinesis.us-west-1.amazonaws.com',
        'kms': 'kms.us-west-1.amazonaws.com',
        'logs': 'logs.us-west-1.amazonaws.com',
        'monitoring': 'monitoring.us-west-1.amazonaws.com',
        'rds': 'rds.us-west-1.amazonaws.com',
        's3': 's3.us-west-1.amazonaws.com',
        'sdb': 'sdb.us-west-1.amazonaws.com',
        'sns': 'sns.us-west-1.amazonaws.com',
        'sqs': 'sqs.us-west-1.amazonaws.com',
        'storagegateway': 'storagegateway.us-west-1.amazonaws.com',
        'streams.dynamodb': 'streams.dynamodb.us-west-1.amazonaws.com',
        'sts': 'sts.us-west-1.amazonaws.com',
        'swf': 'swf.us-west-1.amazonaws.com',
    },
    'us-west-2': {
        'apigateway': 'apigateway.us-west-2.amazonaws.com',
        'autoscaling': 'autoscaling.us-west-2.amazonaws.com',
        'cloudformation': 'cloudformation.us-west-2.amazonaws.com',
        'cloudhsm': 'cloudhsm.us-west-2.amazonaws.com',
        'cloudsearch': 'cloudsearch.us-west-2.amazonaws.com',
        'cloudtrail': 'cloudtrail.us-west-2.amazonaws.com',
        'codedeploy': 'codedeploy.us-west-2.amazonaws.com',
        'codepipeline': 'codepipeline.us-west-2.amazonaws.com',
        'config': 'config.us-west-2.amazonaws.com',
        'datapipeline': 'datapipeline.us-west-2.amazonaws.com',
        'devicefarm': 'devicefarm.us-west-2.amazonaws.com',
        'directconnect': 'directconnect.us-west-2.amazonaws.com',
        'ds': 'ds.us-west-2.amazonaws.com',
        'dynamodb': 'dynamodb.us-west-2.amazonaws.com',
        'ec2': 'ec2.us-west-2.amazonaws.com',
        'ecs': 'ecs.us-west-2.amazonaws.com',
        'elasticache': 'elasticache.us-west-2.amazonaws.com',
        'elasticbeanstalk': 'elasticbeanstalk.us-west-2.amazonaws.com',
        'elasticfilesystem': 'elasticfilesystem.us-west-2.amazonaws.com',
        'elasticloadbalancing': 'elasticloadbalancing.us-west-2.amazonaws.com',
        'elasticmapreduce': 'elasticmapreduce.us-west-2.amazonaws.com',
        'email': 'email.us-west-2.amazonaws.com',
        'glacier': 'glacier.us-west-2.amazonaws.com',
        'iot': 'iot.us-west-2.amazonaws.com',
        'kinesis': 'kinesis.us-west-2.amazonaws.com',
        'kms': 'kms.us-west-2.amazonaws.com',
        'lambda': 'lambda.us-west-2.amazonaws.com',
        'logs': 'logs.us-west-2.amazonaws.com',
        'monitoring': 'monitoring.us-west-2.amazonaws.com',
        'rds': 'rds.us-west-2.amazonaws.com',
        'redshift': 'redshift.us-west-2.amazonaws.com',
        's3': 's3.us-west-2.amazonaws.com',
        'sdb': 'sdb.us-west-2.amazonaws.com',
        'sns': 'sns.us-west-2.amazonaws.com',
        'sqs': 'sqs.us-west-2.amazonaws.com',
        'ssm': 'ssm.us-west-2.amazonaws.com',
        'storagegateway': 'storagegateway.us-west-2.amazonaws.com',
        'streams.dynamodb': 'streams.dynamodb.us-west-2.amazonaws.com',
        'sts': 'sts.us-west-2.amazonaws.com',
        'swf': 'swf.us-west-2.amazonaws.com',
        'workspaces': 'workspaces.us-west-2.amazonaws.com',
    },
}


# Lists the services in the aws partition that do not require a region
# when resolving an endpoint because these services have partitionWide
# endpoints.
KNOWN_AWS_PARTITION_WIDE = {
    'importexport': 'https://importexport.amazonaws.com',
    'cloudfront': 'https://cloudfront.amazonaws.com',
    'waf': 'https://waf.amazonaws.com',
    'route53': 'https://route53.amazonaws.com',
    's3': 'https://s3.amazonaws.com',
    'sts': 'https://sts.amazonaws.com',
    'iam': 'https://iam.amazonaws.com',
}


def _known_endpoints_by_region():
    for region_name, service_dict in KNOWN_REGIONS.items():
        for service_name, endpoint in service_dict.items():
            yield service_name, region_name, endpoint


@pytest.mark.parametrize(
    "service_name, region_name, expected_endpoint",
    _known_endpoints_by_region(),
)
def test_single_service_region_endpoint(
    patched_session, service_name, region_name, expected_endpoint
):
    # Verify the actual values from the partition files.  While
    # TestEndpointHeuristics verified the generic functionality given any
    # endpoints file, this test actually verifies the partition data against a
    # fixed list of known endpoints.  This list doesn't need to be kept 100% up
    # to date, but serves as a basis for regressions as the endpoint data
    # logic evolves.
    resolver = patched_session._get_internal_component('endpoint_resolver')
    bridge = ClientEndpointBridge(resolver, None, None)
    result = bridge.resolve(service_name, region_name)
    expected = f'https://{expected_endpoint}'
    assert result['endpoint_url'] == expected


@pytest.mark.parametrize(
    "service_name, expected_endpoint", KNOWN_AWS_PARTITION_WIDE.items()
)
def test_single_service_partition_endpoint(
    patched_session, service_name, expected_endpoint
):
    resolver = patched_session._get_internal_component('endpoint_resolver')
    bridge = ClientEndpointBridge(resolver)
    result = bridge.resolve(service_name)
    assert result['endpoint_url'] == expected_endpoint


def test_non_partition_endpoint_requires_region(patched_session):
    resolver = patched_session._get_internal_component('endpoint_resolver')
    with pytest.raises(NoRegionError):
        resolver.construct_endpoint('ec2')


class TestEndpointResolution(BaseSessionTest):
    def setUp(self):
        super().setUp()
        self.xml_response = (
            b'<?xml version="1.0" encoding="UTF-8"?>\n\n'
            b'<ListRolesResponse '
            b'xmlns="https://iam.amazonaws.com/doc/2010-05-08/">\n'
            b'<ListRolesResult>\n</ListRolesResult>'
            b'</ListRolesResponse>'
        )

    def create_stubbed_client(self, service_name, region_name, **kwargs):
        client = self.session.create_client(
            service_name, region_name, **kwargs
        )
        http_stubber = ClientHTTPStubber(client)
        http_stubber.start()
        return client, http_stubber

    def test_regionalized_client_endpoint_resolution(self):
        client, stubber = self.create_stubbed_client('s3', 'us-east-2')
        stubber.add_response()
        client.list_buckets()
        self.assertEqual(
            stubber.requests[0].url, 'https://s3.us-east-2.amazonaws.com/'
        )

    def test_regionalized_client_with_unknown_region(self):
        client, stubber = self.create_stubbed_client('s3', 'not-real')
        stubber.add_response()
        client.list_buckets()
        # Validate we don't fall back to partition endpoint for
        # regionalized services.
        self.assertEqual(
            stubber.requests[0].url, 'https://s3.not-real.amazonaws.com/'
        )

    def test_unregionalized_client_endpoint_resolution(self):
        client, stubber = self.create_stubbed_client('iam', 'us-west-2')
        stubber.add_response(body=self.xml_response)
        client.list_roles()
        self.assertTrue(
            stubber.requests[0].url.startswith('https://iam.amazonaws.com/')
        )

    def test_unregionalized_client_with_unknown_region(self):
        client, stubber = self.create_stubbed_client('iam', 'not-real')
        stubber.add_response(body=self.xml_response)
        client.list_roles()
        self.assertTrue(
            stubber.requests[0].url.startswith('https://iam.amazonaws.com/')
        )


@pytest.mark.parametrize("is_builtin", [True, False])
def test_endpoint_resolver_knows_its_datasource(patched_session, is_builtin):
    # The information whether or not the endpoints.json file was loaded from
    # the builtin data directory or not should be passed from Loader to
    # EndpointResolver.
    session = patched_session
    loader = session.get_component('data_loader')
    with mock.patch.object(loader, 'is_builtin_path', return_value=is_builtin):
        resolver = session._get_internal_component('endpoint_resolver')
        assert resolver.uses_builtin_data == is_builtin
