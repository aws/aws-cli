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

from awscli.testutils import BaseAWSPreviewCommandParamsTest as \
    BaseAWSCommandParamsTest


class TestCreateDistribution(BaseAWSCommandParamsTest):

    prefix = 'cloudfront create-distribution '

    def test_origin_domain_name_with_custom_domain(self):
        cmdline = self.prefix + '--origin-domain-name foo.com'
        result = {
            'DistributionConfig': {
                'Origins': {
                    'Quantity': 1,
                    'Items': [{
                        'CustomOriginConfig': mock.ANY,
                        'DomainName': 'foo.com',
                        'Id': mock.ANY,
                        'OriginPath': '',
                    }]
                },
                'CallerReference': mock.ANY,
                'Comment': '',
                'Enabled': True,
                'DefaultCacheBehavior': mock.ANY,
                },
            }
        self.run_cmd(cmdline)
        self.assertEqual(self.last_kwargs, result)

    def test_origin_domain_name_with_s3_domain(self):
        cmdline = self.prefix + '--origin-domain-name foo.s3.amazonaws.com'
        result = {
            'DistributionConfig': {
                'Origins': {
                    'Quantity': 1,
                    'Items': [{
                        'S3OriginConfig': mock.ANY,
                        'DomainName': 'foo.s3.amazonaws.com',
                        'Id': mock.ANY,
                        'OriginPath': '',
                    }]
                },
                'CallerReference': mock.ANY,
                'Comment': '',
                'Enabled': True,
                'DefaultCacheBehavior': mock.ANY,
                },
            }
        self.run_cmd(cmdline)
        self.assertEqual(self.last_kwargs, result)

    def test_s3_domain_with_default_root_object(self):
        cmdline = (self.prefix + '--origin-domain-name foo.s3.amazonaws.com '
                   + '--default-root-object index.html')
        result = {
            'DistributionConfig': {
                'Origins': {
                    'Quantity': 1,
                    'Items': [{
                        'S3OriginConfig': mock.ANY,
                        'DomainName': 'foo.s3.amazonaws.com',
                        'Id': mock.ANY,
                        'OriginPath': '',
                    }]
                },
                'CallerReference': mock.ANY,
                'Comment': '',
                'Enabled': True,
                'DefaultCacheBehavior': mock.ANY,
                'DefaultRootObject': 'index.html',
                },
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
            }
        self.run_cmd(cmdline)
        self.assertEqual(self.last_kwargs, result)

    def test_both_distribution_config_and_origin_domain_name(self):
        self.assert_params_for_cmd(
            self.prefix + '--distribution-config {} --origin-domain-name a.us',
            expected_rc=255,
            stderr_contains='cannot be specified when one of the following')

    def test_no_input(self):
        self.run_cmd(self.prefix, expected_rc=255)
