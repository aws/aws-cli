# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import mock

from awscli.testutils import BaseAWSCommandParamsTest


class TestUpdateDistribution(BaseAWSCommandParamsTest):

    prefix = 'cloudfront update-distribution --id myid '

    def test_default_root_object(self):
        cmdline = self.prefix + '--default-root-object index.html'
        self.parsed_response = {
            # A get-distribution-config response, contains a minimal config
            'ETag': '__etag__',
            'DistributionConfig': {
                'Origins': {
                    'Quantity': 1,
                    'Items': [{'Id': 'foo', 'DomainName': 'bar'}]
                },
                'CallerReference': 'abcd',
                'Comment': '',
                'Enabled': True,
                'DefaultCacheBehavior': {
                    'TargetOriginId': 'foo',
                    'ForwardedValues': {
                        'QueryString': True, 'Cookies': {'Forward': 'none'}},
                    'TrustedSigners': {'Enabled': True, 'Quantity': 0},
                    'ViewerProtocolPolicy': 'allow-all',
                    'MinTTL': 0,
                    },
                },
            }
        result = {
            'DistributionConfig': {
                'DefaultRootObject': 'index.html',
                'Origins': {
                    'Quantity': 1,
                    'Items': [{'Id': 'foo', 'DomainName': 'bar'}]
                },
                'CallerReference': 'abcd',
                'Comment': '',
                'Enabled': True,
                'DefaultCacheBehavior': mock.ANY,
                },
            'Id': 'myid',
            'IfMatch': '__etag__',
            }
        self.run_cmd(cmdline)
        self.assertEqual(self.last_kwargs, result)

    def test_distribution_config(self):
        # To demonstrate the original --distribution-config still works
        cmdline = self.prefix + ('--distribution-config '
            'Origins={Quantity=1,Items=[{Id=foo,DomainName=bar}]},'
            'DefaultCacheBehavior={'
                'TargetOriginId=foo,'
                'ForwardedValues={QueryString=False,Cookies={Forward=none}},'
                'TrustedSigners={Enabled=True,Quantity=0},'
                'ViewerProtocolPolicy=allow-all,'
                'MinTTL=0'
                '},'
            'CallerReference=abcd,'
            'Enabled=True,'
            'Comment='
            )
        result = {
            'DistributionConfig': {
                'Origins': {
                    'Quantity': 1,
                    'Items': [{'Id': 'foo', 'DomainName': 'bar'}]
                },
                'CallerReference': 'abcd',
                'Comment': '',
                'Enabled': True,
                'DefaultCacheBehavior': mock.ANY,
                },
            'Id': 'myid',
            }
        self.run_cmd(cmdline)
        self.assertEqual(self.last_kwargs, result)

    def test_both_distribution_config_and_default_root_object(self):
        self.assert_params_for_cmd(
            self.prefix + '--distribution-config {} --default-root-object foo',
            expected_rc=252,
            stderr_contains='cannot be specified when one of the following')

    def test_no_input(self):
        self.run_cmd(self.prefix, expected_rc=252)
