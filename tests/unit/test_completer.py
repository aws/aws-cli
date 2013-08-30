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
import pprint
import logging
import difflib

from awscli.completer import complete

LOG = logging.getLogger(__name__)

COMPLETIONS = [
    ('aws ', -1, set(['autoscaling', 'cloudformation', 'cloudfront',
                      'cloudsearch', 'cloudwatch', 'datapipeline',
                      'directconnect', 'dynamodb', 'ec2', 'elasticache',
                      'elasticbeanstalk', 'elastictranscoder', 'elb', 'emr',
                      'iam', 'importexport', 'opsworks', 'rds', 'redshift',
                      'route53', 's3', 's3api', 'ses', 'sns', 'sqs',
                      'storagegateway', 'sts', 'support', 'swf'])),
    ('aws cloud', -1, set(['cloudformation', 'cloudfront',
                           'cloudsearch', 'cloudwatch'])),
    ('aws cloudf', -1, set(['cloudformation', 'cloudfront'])),
    ('aws cloudfr', -1, set(['cloudfront'])),
    ('aws foobar', -1, set([])),
    ('aws  --', -1, set(['--debug', '--endpoint-url', '--no-verify-ssl',
                         '--no-paginate', '--output', '--profile',
                         '--region', '--version', '--color'])),
    ('aws  --re', -1, set(['--region'])),
    ('aws sts ', -1, set(['assume-role', 'get-federation-token',
                          'decode-authorization-message',
                          'assume-role-with-web-identity',
                          'get-session-token', 'help'])),
    ('aws sts de', -1, set(['decode-authorization-message'])),
    ('aws sts --', -1, set(['--debug', '--endpoint-url', '--no-verify-ssl',
                            '--no-paginate', '--output', '--profile',
                            '--region', '--version', '--color'])),
    ('aws sts decode-authorization-message ', -1, set(['--encoded-message'])),
    ('aws sts decode-authorization-message --encoded-message --re', -1,
     set(['--region']))
    ]

_COMPLETIONS = [
    ('aws ', -1, ('autoscaling', 'cloudformation', 'cloudfront',
                  'cloudsearch', 'cloudwatch', 'datapipeline',
                  'directconnect', 'dynamodb', 'ec2', 'elasticache',
                  'elasticbeanstalk', 'elastictranscoder', 'elb', 'emr',
                  'iam', 'importexport', 'opsworks', 'rds', 'redshift',
                  'route53', 's3', 'ses', 'sns', 'sqs', 'storagegateway',
                  'sts', 'support', 'swf')),
    ('aws cloud', -1, ('cloudformation', 'cloudfront',
                       'cloudsearch', 'cloudwatch')),
    ('aws cloudf', -1, ('cloudformation', 'cloudfront')),
    ('aws cloudfr', -1, ('cloudfront',)),
    ('aws sts ', -1, ('assume-role', 'get-federation-token',
                      'decode-authorization-message',
                      'assume-role-with-web-identity',
                      'get-session-token')),
    ('aws sts de', -1, ('decode-authorization-message',)),
    ('aws sts --', -1, ('--debug', '--endpoint-url', '--no-verify-ssl',
                        '--no-paginate', '--output', '--profile',
                        '--region', '--version', '--color')),
    ('aws sts decode-authorization-message ', -1, ('--encoded-message',)),
    ('aws sts decode-authorization-message --encoded-message --re', -1,
     ('--region',))
    ]


def check_dicts(xmlfile, d1, d2):
    if d1 != d2:
        LOG.debug('-' * 40)
        LOG.debug(xmlfile)
        LOG.debug('-' * 40)
        LOG.debug(pprint.pformat(d1))
        LOG.debug('-' * 40)
        LOG.debug(pprint.pformat(d2))
    if not d1 == d2:
        # Borrowed from assertDictEqual, though this doesn't
        # handle the case when unicode literals are used in one
        # dict but not in the other (and we want to consider them
        # as being equal).
        pretty_d1 = pprint.pformat(d1, width=1).splitlines()
        pretty_d2 = pprint.pformat(d2, width=1).splitlines()
        diff = ('\n' + '\n'.join(difflib.ndiff(pretty_d1, pretty_d2)))
        raise AssertionError("Dicts are not equal:\n%s" % diff)

def check_completer(cmdline, results, expected_results):
    if results != expected_results:
        LOG.debug('-' * 40)
        LOG.debug(cmdline)
        LOG.debug('-' * 40)
        LOG.debug(pprint.pformat(results))
        LOG.debug('-' * 40)
        LOG.debug(pprint.pformat(expected_results))
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
    for cmdline, point, expected_results in COMPLETIONS:
        if point == -1:
            point = len(cmdline)
        results = complete(cmdline, point)
        if results is not None:
            results = set(complete(cmdline, point))
        yield check_completer, cmdline, results, expected_results
