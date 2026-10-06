# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import random
import time

from awscli.arguments import CustomArgument


def unique_string(prefix='cli'):
    return '%s-%s-%s' % (prefix, int(time.time()), random.randint(1, 1000000))


def add_paths_argument(argument_table, **kwargs):
    argument_table['invalidation-batch'].required = False
    argument_table['paths'] = PathsArgument()


class PathsArgument(CustomArgument):
    def __init__(self):
        doc = (
            'The space-separated paths to be invalidated.'
            ' Note: --invalidation-batch and --paths are mutually exclusive.'
        )
        super(PathsArgument, self).__init__('paths', nargs='+', help_text=doc)

    def add_to_params(self, parameters, value):
        if value is not None:
            parameters['InvalidationBatch'] = {
                "CallerReference": unique_string(),
                "Paths": {"Quantity": len(value), "Items": value},
            }


class ExclusiveArgument(CustomArgument):
    DOC = '%s This argument and --%s are mutually exclusive.'

    def __init__(
        self,
        name,
        argument_table,
        exclusive_to='distribution-config',
        help_text='',
    ):
        argument_table[exclusive_to].required = False
        super(ExclusiveArgument, self).__init__(
            name, help_text=self.DOC % (help_text, exclusive_to)
        )

    def distribution_config_template(self):
        return {
            "CallerReference": unique_string(),
            "Origins": {"Quantity": 0, "Items": []},
            "DefaultCacheBehavior": {
                "TargetOriginId": "placeholder",
                "ForwardedValues": {
                    "QueryString": False,
                    "Cookies": {"Forward": "none"},
                },
                "TrustedSigners": {"Enabled": False, "Quantity": 0},
                "ViewerProtocolPolicy": "allow-all",
                "MinTTL": 0,
            },
            "Enabled": True,
            "Comment": "",
        }


class OriginDomainName(ExclusiveArgument):
    def __init__(self, argument_table):
        super(OriginDomainName, self).__init__(
            'origin-domain-name',
            argument_table,
            help_text='The domain name for your origin.',
        )

    def add_to_params(self, parameters, value):
        if value is None:
            return
        parameters.setdefault(
            'DistributionConfig', self.distribution_config_template()
        )
        origin_id = unique_string(prefix=value)
        item = {"Id": origin_id, "DomainName": value, "OriginPath": ''}
        if item['DomainName'].endswith('.s3.amazonaws.com'):
            # We do not need to detect '.s3[\w-].amazonaws.com' as S3 buckets,
            # because CloudFront treats GovCloud S3 buckets as custom domain.
            # http://docs.aws.amazon.com/govcloud-us/latest/UserGuide/setting-up-cloudfront.html
            item["S3OriginConfig"] = {"OriginAccessIdentity": ""}
        else:
            item["CustomOriginConfig"] = {
                'HTTPPort': 80,
                'HTTPSPort': 443,
                'OriginProtocolPolicy': 'http-only',
            }
        parameters['DistributionConfig']['Origins'] = {
            "Quantity": 1,
            "Items": [item],
        }
        parameters['DistributionConfig']['DefaultCacheBehavior'][
            'TargetOriginId'
        ] = origin_id


class CreateDefaultRootObject(ExclusiveArgument):
    def __init__(self, argument_table, help_text=''):
        super(CreateDefaultRootObject, self).__init__(
            'default-root-object',
            argument_table,
            help_text=help_text
            or (
                'The object that you want CloudFront to return (for example, '
                'index.html) when a viewer request points to your root URL.'
            ),
        )

    def add_to_params(self, parameters, value):
        if value is not None:
            parameters.setdefault(
                'DistributionConfig', self.distribution_config_template()
            )
            parameters['DistributionConfig']['DefaultRootObject'] = value


class UpdateDefaultRootObject(CreateDefaultRootObject):
    def __init__(self, context, argument_table):
        super(UpdateDefaultRootObject, self).__init__(
            argument_table,
            help_text=(
                'The object that you want CloudFront to return (for example, '
                'index.html) when a viewer request points to your root URL. '
                'CLI will automatically make a get-distribution-config call '
                'to load and preserve your other settings.'
            ),
        )
        self.context = context

    def add_to_params(self, parameters, value):
        if value is not None:
            client = self.context['session'].create_client(
                'cloudfront',
                region_name=self.context['parsed_args'].region,
                endpoint_url=self.context['parsed_args'].endpoint_url,
                verify=self.context['parsed_args'].verify_ssl,
            )
            response = client.get_distribution_config(Id=parameters['Id'])
            parameters['IfMatch'] = response['ETag']
            parameters['DistributionConfig'] = response['DistributionConfig']
            parameters['DistributionConfig']['DefaultRootObject'] = value
