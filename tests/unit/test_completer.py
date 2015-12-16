# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import create_clidriver
import os
import pprint
import logging
import difflib

import mock

from awscli.completer import Completer

LOG = logging.getLogger(__name__)


GLOBALOPTS = ['--debug', '--endpoint-url', '--no-verify-ssl', '--no-paginate',
              '--output', '--profile', '--region', '--version', '--color',
              '--query', '--no-sign-request', '--ca-bundle',
              '--cli-read-timeout', '--cli-connect-timeout']

COMPLETIONS = [
    ('aws ', -1, set(['apigateway', 'autoscaling', 'cloudformation', 'cloudfront',
                      'cloudhsm', 'cloudsearch', 'cloudsearchdomain',
                      'cloudtrail', 'cloudwatch', 'cognito-identity',
                      'codecommit', 'codepipeline', 'cognito-sync',
                      'configservice', 'configure', 'datapipeline', 'deploy',
                      'devicefarm', 'directconnect', 'ds', 'dynamodb',
                      'dynamodbstreams', 'glacier', 'ec2', 'ecr', 'ecs', 'efs',
                      'elasticache', 'elasticbeanstalk', 'elastictranscoder',
                      'elb', 'emr', 'es', 'firehose',
                      'iam', 'iot', 'iot-data', 'importexport', 'inspector',
                      'kinesis', 'kms',
                      'lambda', 'logs', 'marketplacecommerceanalytics',
                      'machinelearning', 'opsworks', 'rds',
                      'redshift', 'route53', 'route53domains', 's3', 's3api',
                      'sdb', 'ses', 'sns', 'sqs', 'ssm', 'storagegateway', 'sts',
                      'ssm', 'support', 'swf', 'waf', 'workspaces'])),
    ('aws cloud', -1, set(['cloudformation', 'cloudfront', 'cloudhsm',
                           'cloudsearch', 'cloudsearchdomain', 'cloudtrail',
                           'cloudwatch'])),
    ('aws cloudf', -1, set(['cloudformation', 'cloudfront',])),
    ('aws cloudfr', -1, set(['cloudfront'])),
    ('aws foobar', -1, set([])),
    ('aws  --', -1, set(GLOBALOPTS)),
    ('aws  --re', -1, set(['--region'])),
    ('aws sts ', -1, set(['assume-role', 'assume-role-with-saml',
                          'get-federation-token',
                          'decode-authorization-message',
                          'assume-role-with-web-identity',
                          'get-session-token'])),
    ('aws sts --debug --de', -1, set([])),
    ('aws sts de', -1, set(['decode-authorization-message'])),
    ('aws sts --', -1, set(GLOBALOPTS)),
    ('aws sts decode-authorization-message', -1, set([])),
    ('aws sts decode-authorization-message --encoded-message --re', -1,
     set(['--region'])),
    ('aws sts decode-authorization-message --encoded-message --enco', -1,
     set([])),
    ('aws ec2 --debug describe-instances --instance-ids ', -1,
     set([])),
    ('aws ec2 --debug describe-instances --instance-ids i-12345678 - ', -1,
     set(['--filters', '--dry-run', '--no-dry-run', '--endpoint-url',
          '--no-verify-ssl', '--no-paginate', '--no-sign-request', '--output',
          '--profile', '--starting-token', '--max-items', '--page-size',
          '--region', '--version', '--color', '--query', '--ca-bundle',
          '--generate-cli-skeleton', '--cli-input-json', '--cli-read-timeout',
          '--cli-connect-timeout'])),
    ('aws s3', -1, set(['cp', 'mv', 'rm', 'mb', 'rb', 'ls', 'sync', 'website'])),
    ('aws s3 m', -1, set(['mv', 'mb'])),
    ('aws s3 cp -', -1, set(['--no-guess-mime-type', '--dryrun',
                             '--recursive', '--website-redirect',
                             '--quiet', '--acl', '--storage-class',
                             '--sse', '--sse-c', '--sse-c-copy-source',
                             '--sse-c-copy-source-key',
                             '--sse-c-key',
                             '--sse-kms-key-id',
                             '--exclude', '--include',
                             '--follow-symlinks', '--no-follow-symlinks',
                             '--cache-control', '--content-type',
                             '--content-disposition', '--source-region',
                             '--content-encoding', '--content-language',
                             '--expires', '--grants', '--only-show-errors',
                             '--expected-size', '--page-size',
                             '--metadata', '--metadata-directive',
                             '--ignore-glacier-warnings']
                            + GLOBALOPTS)),
    ('aws s3 cp --quiet -', -1, set(['--no-guess-mime-type', '--dryrun',
                                     '--recursive', '--content-type',
                                     '--follow-symlinks', '--no-follow-symlinks',
                                     '--content-disposition', '--cache-control',
                                     '--content-encoding', '--content-language',
                                     '--expires', '--website-redirect', '--acl',
                                     '--storage-class', '--sse', '--sse-c',
                                     '--sse-c-copy-source',
                                     '--sse-c-copy-source-key',
                                     '--sse-c-key',
                                     '--sse-kms-key-id',
                                     '--exclude', '--include',
                                     '--source-region', '--metadata',
                                     '--metadata-directive',
                                     '--grants', '--only-show-errors',
                                     '--expected-size', '--page-size',
                                     '--ignore-glacier-warnings']
                                    + GLOBALOPTS)),
    ('aws emr ', -1, set(['add-instance-groups', 'add-steps', 'add-tags',
                          'create-cluster', 'create-default-roles',
                          'create-hbase-backup', 'describe-cluster',
                          'describe-step', 'disable-hbase-backups', 'get',
                          'install-applications', 'list-clusters',
                          'list-instances', 'list-steps',
                          'modify-cluster-attributes', 'modify-instance-groups',
                          'put', 'remove-tags', 'restore-from-hbase-backup',
                          'schedule-hbase-backup', 'socks', 'ssh',
                          'terminate-clusters', 'wait']))
]


def check_completer(cmdline, results, expected_results):
    if not results == expected_results:
        # Borrowed from assertDictEqual, though this doesn't
        # handle the case when unicode literals are used in one
        # dict but not in the other (and we want to consider them
        # as being equal).
        pretty_d1 = pprint.pformat(results, width=1).splitlines()
        pretty_d2 = pprint.pformat(expected_results, width=1).splitlines()
        diff = ('\n' + '\n'.join(difflib.ndiff(pretty_d1, pretty_d2)))
        raise AssertionError("Results are not equal:\n%s" % diff)
    assert results == expected_results


def test_completions():
    environ = {
        'AWS_DATA_PATH': os.environ['AWS_DATA_PATH'],
        'AWS_DEFAULT_REGION': 'us-east-1',
        'AWS_ACCESS_KEY_ID': 'access_key',
        'AWS_SECRET_ACCESS_KEY': 'secret_key',
        'AWS_CA_BUNDLE': 'ca_bundle',
        'AWS_CONFIG_FILE': '',
    }
    with mock.patch('os.environ', environ):
        completer = Completer()
        completer.clidriver = create_clidriver()
        for cmdline, point, expected_results in COMPLETIONS:
            if point == -1:
                point = len(cmdline)
            results = set(completer.complete(cmdline, point))
            yield check_completer, cmdline, results, expected_results
