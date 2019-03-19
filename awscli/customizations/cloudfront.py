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
import sys
import time
import random

import rsa
from botocore.utils import parse_to_aware_datetime
from botocore.signers import CloudFrontSigner

from awscli.arguments import CustomArgument
from awscli.customizations.utils import validate_mutually_exclusive_handler
from awscli.customizations.commands import BasicCommand


def register(event_handler):
    event_handler.register('building-command-table.cloudfront', _add_sign)

    # Provides a simpler --paths for ``aws cloudfront create-invalidation``
    event_handler.register(
        'building-argument-table.cloudfront.create-invalidation', _add_paths)
    event_handler.register(
        'operation-args-parsed.cloudfront.create-invalidation',
        validate_mutually_exclusive_handler(['invalidation_batch'], ['paths']))

    event_handler.register(
        'operation-args-parsed.cloudfront.create-distribution',
        validate_mutually_exclusive_handler(
            ['default_root_object', 'origin_domain_name'],
            ['distribution_config']))
    event_handler.register(
        'building-argument-table.cloudfront.create-distribution',
        lambda argument_table, **kwargs: argument_table.__setitem__(
            'origin-domain-name', OriginDomainName(argument_table)))
    event_handler.register(
        'building-argument-table.cloudfront.create-distribution',
        lambda argument_table, **kwargs: argument_table.__setitem__(
            'default-root-object', CreateDefaultRootObject(argument_table)))

    context = {}
    event_handler.register(
        'top-level-args-parsed', context.update, unique_id='cloudfront')
    event_handler.register(
        'operation-args-parsed.cloudfront.update-distribution',
        validate_mutually_exclusive_handler(
            ['default_root_object'], ['distribution_config']))
    event_handler.register(
        'building-argument-table.cloudfront.update-distribution',
        lambda argument_table, **kwargs: argument_table.__setitem__(
            'default-root-object', UpdateDefaultRootObject(
                context=context, argument_table=argument_table)))


def unique_string(prefix='cli'):
    return '%s-%s-%s' % (prefix, int(time.time()), random.randint(1, 1000000))


def _add_paths(argument_table, **kwargs):
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

    def __init__(self, name, argument_table,
                 exclusive_to='distribution-config', help_text=''):
        argument_table[exclusive_to].required = False
        super(ExclusiveArgument, self).__init__(
            name, help_text=self.DOC % (help_text, exclusive_to))

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
                "TrustedSigners": {
                    "Enabled": False,
                    "Quantity": 0
                },
                "ViewerProtocolPolicy": "allow-all",
                "MinTTL": 0
            },
            "Enabled": True,
            "Comment": "",
        }


class OriginDomainName(ExclusiveArgument):
    def __init__(self, argument_table):
        super(OriginDomainName, self).__init__(
            'origin-domain-name', argument_table,
            help_text='The domain name for your origin.')

    def add_to_params(self, parameters, value):
        if value is None:
            return
        parameters.setdefault(
            'DistributionConfig', self.distribution_config_template())
        origin_id = unique_string(prefix=value)
        item = {"Id": origin_id, "DomainName": value, "OriginPath": ''}
        if item['DomainName'].endswith('.s3.amazonaws.com'):
            # We do not need to detect '.s3[\w-].amazonaws.com' as S3 buckets,
            # because CloudFront treats GovCloud S3 buckets as custom domain.
            # http://docs.aws.amazon.com/govcloud-us/latest/UserGuide/setting-up-cloudfront.html
            item["S3OriginConfig"] = {"OriginAccessIdentity": ""}
        else:
            item["CustomOriginConfig"] = {
                'HTTPPort': 80, 'HTTPSPort': 443,
                'OriginProtocolPolicy': 'http-only'}
        parameters['DistributionConfig']['Origins'] = {
            "Quantity": 1, "Items": [item]}
        parameters['DistributionConfig']['DefaultCacheBehavior'][
            'TargetOriginId'] = origin_id


class CreateDefaultRootObject(ExclusiveArgument):
    def __init__(self, argument_table, help_text=''):
        super(CreateDefaultRootObject, self).__init__(
            'default-root-object', argument_table, help_text=help_text or (
                'The object that you want CloudFront to return (for example, '
                'index.html) when a viewer request points to your root URL.'))

    def add_to_params(self, parameters, value):
        if value is not None:
            parameters.setdefault(
                'DistributionConfig', self.distribution_config_template())
            parameters['DistributionConfig']['DefaultRootObject'] = value


class UpdateDefaultRootObject(CreateDefaultRootObject):
    def __init__(self, context, argument_table):
        super(UpdateDefaultRootObject, self).__init__(
            argument_table, help_text=(
                'The object that you want CloudFront to return (for example, '
                'index.html) when a viewer request points to your root URL. '
                'CLI will automatically make a get-distribution-config call '
                'to load and preserve your other settings.'))
        self.context = context

    def add_to_params(self, parameters, value):
        if value is not None:
            client = self.context['session'].create_client(
                'cloudfront',
                region_name=self.context['parsed_args'].region,
                endpoint_url=self.context['parsed_args'].endpoint_url,
                verify=self.context['parsed_args'].verify_ssl)
            response = client.get_distribution_config(Id=parameters['Id'])
            parameters['IfMatch'] = response['ETag']
            parameters['DistributionConfig'] = response['DistributionConfig']
            parameters['DistributionConfig']['DefaultRootObject'] = value


def _add_sign(command_table, session, **kwargs):
    command_table['sign'] = SignCommand(session)


class SignCommand(BasicCommand):
    NAME = 'sign'
    DESCRIPTION = 'Sign a given url.'
    DATE_FORMAT = """Supported formats include:
        YYYY-MM-DD (which means 0AM UTC of that day),
        YYYY-MM-DDThh:mm:ss (with default timezone as UTC),
        YYYY-MM-DDThh:mm:ss+hh:mm or YYYY-MM-DDThh:mm:ss-hh:mm (with offset),
        or EpochTime (which always means UTC).
        Do NOT use YYYYMMDD, because it will be treated as EpochTime."""
    ARG_TABLE = [
        {
            'name': 'url',
            'no_paramfile': True,  # To disable the default paramfile behavior
            'required': True,
            'help_text': 'The URL to be signed',
        },
        {
            'name': 'key-pair-id',
            'required': True,
            'help_text': (
                "The active CloudFront key pair Id for the key pair "
                "that you're using to generate the signature."),
        },
        {
            'name': 'private-key',
            'required': True,
            'help_text': 'file://path/to/your/private-key.pem',
        },
        {
            'name': 'date-less-than', 'required': True,
            'help_text':
                'The expiration date and time for the URL. ' + DATE_FORMAT,
        },
        {
            'name': 'date-greater-than',
            'help_text':
                'An optional start date and time for the URL. ' + DATE_FORMAT,
        },
        {
            'name': 'ip-address',
            'help_text': (
                'An optional IP address or IP address range to allow client '
                'making the GET request from. Format: x.x.x.x/x or x.x.x.x'),
        },
    ]

    def _run_main(self, args, parsed_globals):
        signer = CloudFrontSigner(
            args.key_pair_id, RSASigner(args.private_key).sign)
        date_less_than = parse_to_aware_datetime(args.date_less_than)
        date_greater_than = args.date_greater_than
        if date_greater_than is not None:
            date_greater_than = parse_to_aware_datetime(date_greater_than)
        if date_greater_than is not None or args.ip_address is not None:
            policy = signer.build_policy(
                args.url, date_less_than, date_greater_than=date_greater_than,
                ip_address=args.ip_address)
            sys.stdout.write(signer.generate_presigned_url(
                args.url, policy=policy))
        else:
            sys.stdout.write(signer.generate_presigned_url(
                args.url, date_less_than=date_less_than))
        return 0


class RSASigner(object):
    def __init__(self, private_key):
        self.priv_key = rsa.PrivateKey.load_pkcs1(private_key.encode('utf8'))

    def sign(self, message):
        return rsa.sign(message, self.priv_key, 'SHA-1')
