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
import os
import pprint
import logging
import difflib

import mock

from awscli.completer import Completer

LOG = logging.getLogger(__name__)

GLOBALOPTS = ['--debug', '--endpoint-url', '--no-verify-ssl',
              '--no-paginate', '--output', '--profile',
              '--region', '--version', '--color', '--query']

COMPLETIONS = [
    ('aws ', -1, set(['autoscaling', 'cloudformation', 'cloudfront',
                      'cloudsearch', 'cloudtrail', 'cloudwatch', 'configure',
                      'datapipeline', 'directconnect', 'dynamodb', 'ec2',
                      'elasticache', 'elasticbeanstalk', 'elastictranscoder',
                      'elb', 'emr', 'iam', 'importexport', 'kinesis',
                      'opsworks', 'rds', 'redshift', 'route53', 's3', 's3api',
                      'sdb', 'ses', 'sns', 'sqs', 'storagegateway', 'sts',
                      'support', 'swf'])),
    ('aws cloud', -1, set(['cloudformation', 'cloudfront',
                           'cloudsearch', 'cloudtrail', 'cloudwatch'])),
    ('aws cloudf', -1, set(['cloudformation', 'cloudfront'])),
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
    ('aws ec2 --region ', -1, set(['us-east-1', 'ap-northeast-1',
                                   'sa-east-1', 'ap-southeast-1',
                                   'ap-southeast-2', 'us-west-2',
                                   'us-west-1', 'eu-west-1',
                                   'us-gov-west-1', 'fips-us-gov-west-1',
                                   'cn-north-1'])),
    ('aws ec2 --debug describe-instances --instance-ids ', -1,
     set([])),
    ('aws ec2 --debug describe-instances --instance-ids i-12345678 - ', -1,
     set(['--filters', '--dry-run', '--no-dry-run', '--endpoint-url',
          '--no-verify-ssl', '--no-paginate', '--output', '--profile',
          '--starting-token', '--max-items',
          '--region', '--version', '--color', '--query'])),
    ('aws s3', -1, set(['cp', 'mv', 'rm', 'mb', 'rb', 'ls', 'sync', 'website'])),
    ('aws s3 m', -1, set(['mv', 'mb'])),
    ('aws s3 cp -', -1, set(['--no-guess-mime-type', '--dryrun',
                             '--recursive', '--website-redirect',
                             '--quiet', '--acl', '--storage-class',
                             '--sse', '--exclude', '--include',
                             '--cache-control', '--content-type',
                             '--content-disposition',
                             '--content-encoding', '--content-language',
                             '--expires', '--grants'] + GLOBALOPTS)),
    ('aws s3 cp --quiet -', -1, set(['--no-guess-mime-type', '--dryrun',
                                     '--recursive', '--content-type',
                                     '--content-disposition', '--cache-control',
                                     '--content-encoding', '--content-language',
                                     '--expires', '--website-redirect', '--acl',
                                     '--storage-class', '--sse',
                                     '--exclude', '--include',
                                     '--grants'] + GLOBALOPTS)),
    ('aws emr ', -1, set([])),
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
        'AWS_CONFIG_FILE': '',
    }
    with mock.patch('os.environ', environ):
        completer = Completer()
        for cmdline, point, expected_results in COMPLETIONS:
            if point == -1:
                point = len(cmdline)
            results = set(completer.complete(cmdline, point))
            yield check_completer, cmdline, results, expected_results
