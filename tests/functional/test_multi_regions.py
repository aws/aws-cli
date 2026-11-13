# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import re
import socket

from botocore import UNSIGNED
from botocore.credentials import CredentialResolver
from botocore.exceptions import (
    ConnectionClosedError,
    EndpointConnectionError,
    NoCredentialsError,
    UnauthorizedSSOTokenError,
)

from awscli.alias import AliasLoader
from awscli.clidriver import AWSCLIEntryPoint
from awscli.constants import (
    CLIENT_ERROR_RC,
    CONFIGURATION_ERROR_RC,
    GENERAL_ERROR_RC,
    PARAM_VALIDATION_ERROR_RC,
)
from awscli.testutils import (
    BaseAWSCommandParamsTest,
    BaseAWSHelpOutputTest,
    FileCreator,
    create_clidriver,
    mock,
)

# A service with no endpoint data in the aws partition.  Where such a
# service exists can only be discovered by calling a region, so a
# hostname that does not resolve means "not here" rather than an error.
SERVICE_WITHOUT_ENDPOINTS = 'dsql'


def vpc_response(vpc_id):
    return {'Vpcs': [{'VpcId': vpc_id, 'CidrBlock': '10.0.0.0/16'}]}


def name_resolution_failure(endpoint_url):
    """The error botocore raises for a hostname that does not exist."""
    return EndpointConnectionError(
        endpoint_url=endpoint_url,
        error=socket.gaierror(
            socket.EAI_NONAME, 'nodename nor servname provided, or not known'
        ),
    )


class BaseMultiRegionTest(BaseAWSCommandParamsTest):
    def setUp(self):
        super().setUp()
        self.request_urls = []
        self.signature_versions = []
        self.user_agents = []

    def before_call(self, params, **kwargs):
        super().before_call(params, **kwargs)
        self.request_urls.append(params['url'])
        self.user_agents.append(params['headers'].get('User-Agent'))
        signer = kwargs.get('request_signer')
        self.signature_versions.append(
            getattr(signer, 'signature_version', None)
        )

    def _request_patch_side_effect(self, *args, **kwargs):
        # An exception queued in ``parsed_responses`` is raised instead of
        # being returned, which is where botocore itself raises a
        # transport or signing failure.
        if self.parsed_responses and isinstance(
            self.parsed_responses[0], Exception
        ):
            raise self.parsed_responses.pop(0)
        return super()._request_patch_side_effect(*args, **kwargs)

    @property
    def called_regions(self):
        regions = []
        for url in self.request_urls:
            match = re.match(
                r'https://[^.]+\.([^.]+)\.(?:amazonaws\.com|api\.aws)', url
            )
            regions.append(match.group(1) if match else url)
        return regions


class TestMultiRegionOutput(BaseMultiRegionTest):
    def test_merges_responses_from_every_region(self):
        self.parsed_responses = [
            vpc_response('vpc-us-east-1'),
            vpc_response('vpc-eu-west-1'),
        ]
        stdout, _, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1'
        )
        self.assertEqual(self.called_regions, ['us-east-1', 'eu-west-1'])
        self.assertEqual(
            json.loads(stdout),
            {
                'Vpcs': [
                    {
                        'VpcId': 'vpc-us-east-1',
                        'CidrBlock': '10.0.0.0/16',
                        '_CliScope': {'Region': 'us-east-1'},
                    },
                    {
                        'VpcId': 'vpc-eu-west-1',
                        'CidrBlock': '10.0.0.0/16',
                        '_CliScope': {'Region': 'eu-west-1'},
                    },
                ]
            },
        )

    def test_keeps_region_order_from_command_line(self):
        self.parsed_responses = [
            vpc_response('vpc-eu-west-1'),
            vpc_response('vpc-us-east-1'),
        ]
        stdout, _, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions eu-west-1,us-east-1'
        )
        self.assertEqual(self.called_regions, ['eu-west-1', 'us-east-1'])
        vpcs = json.loads(stdout)['Vpcs']
        self.assertEqual(
            [vpc['_CliScope']['Region'] for vpc in vpcs],
            ['eu-west-1', 'us-east-1'],
        )

    def test_same_params_sent_to_every_region(self):
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        self.run_cmd(
            'ec2 describe-vpcs --vpc-ids vpc-1 '
            '--multi-regions us-east-1,eu-west-1'
        )
        self.assertEqual(
            [params for _, params in self.operations_called],
            [{'VpcIds': ['vpc-1']}, {'VpcIds': ['vpc-1']}],
        )

    def test_query_applies_to_merged_response(self):
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        stdout, _, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '
            '--query Vpcs[].[VpcId,_CliScope.Region]'
        )
        self.assertEqual(
            json.loads(stdout),
            [['vpc-1', 'us-east-1'], ['vpc-2', 'eu-west-1']],
        )

    def test_yaml_stream_prints_one_entry_per_region(self):
        # yaml-stream writes each region as it finishes, in the same
        # shape it writes each page of a paginated response.
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        stdout, _, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '
            '--output yaml-stream'
        )
        entries = self.yaml.load(stdout)
        self.assertEqual(len(entries), 2)
        self.assertEqual(
            [entry['Vpcs'][0]['_CliScope']['Region'] for entry in entries],
            ['us-east-1', 'eu-west-1'],
        )

    def test_text_output_includes_region(self):
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        stdout, _, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '
            '--output text'
        )
        self.assertIn('us-east-1', stdout)
        self.assertIn('eu-west-1', stdout)

    def test_table_output_includes_region(self):
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        stdout, _, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '
            '--output table'
        )
        self.assertIn('us-east-1', stdout)
        self.assertIn('eu-west-1', stdout)

    def test_off_output_still_calls_every_region(self):
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        stdout, _, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '
            '--output off'
        )
        self.assertEqual(stdout, '')
        self.assertEqual(self.called_regions, ['us-east-1', 'eu-west-1'])

    def test_structure_is_stable_for_a_single_region(self):
        self.parsed_responses = [vpc_response('vpc-1')]
        stdout, _, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1'
        )
        self.assertEqual(
            json.loads(stdout)['Vpcs'][0]['_CliScope'],
            {'Region': 'us-east-1'},
        )

    def test_paginated_response_is_merged(self):
        self.parsed_responses = [
            {
                'Vpcs': [{'VpcId': 'vpc-1'}],
                'NextToken': 'token',
            },
            {'Vpcs': [{'VpcId': 'vpc-2'}]},
            {'Vpcs': [{'VpcId': 'vpc-3'}]},
        ]
        stdout, _, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1'
        )
        response = json.loads(stdout)
        self.assertEqual(
            [vpc['VpcId'] for vpc in response['Vpcs']],
            ['vpc-1', 'vpc-2', 'vpc-3'],
        )
        self.assertNotIn('NextToken', response)
        self.assertEqual(
            self.called_regions, ['us-east-1', 'us-east-1', 'eu-west-1']
        )


class TestMultiRegionErrors(BaseMultiRegionTest):
    """The first region that fails fails the whole command."""

    def test_a_failing_region_stops_the_command(self):
        self.parsed_responses = [
            vpc_response('vpc-1'),
            {
                'Error': {
                    'Code': 'AccessDenied',
                    'Message': 'explicit deny in a service control policy',
                }
            },
            vpc_response('vpc-3'),
        ]
        stdout, stderr, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,ap-south-1,eu-west-1',
            expected_rc=CLIENT_ERROR_RC,
        )
        # Nothing is printed and the remaining region is not called.
        self.assertEqual(stdout, '')
        self.assertEqual(self.called_regions, ['us-east-1', 'ap-south-1'])
        # Reported by the CLI's error handler, like a single-region error.
        self.assertEqual(
            stderr,
            '\naws: [ERROR]: [ap-south-1] An error occurred (AccessDenied) '
            'when calling the DescribeVpcs operation: explicit deny in a '
            'service control policy\n',
        )

    def test_a_failure_in_the_first_region_calls_no_other(self):
        self.parsed_responses = [
            {'Error': {'Code': 'AccessDenied', 'Message': 'denied'}},
            vpc_response('vpc-2'),
        ]
        stdout, stderr, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1',
            expected_rc=CLIENT_ERROR_RC,
        )
        self.assertEqual(stdout, '')
        self.assertEqual(self.called_regions, ['us-east-1'])
        self.assertIn('[us-east-1] An error occurred (AccessDenied)', stderr)

    def test_a_connection_failure_also_stops_the_command(self):
        self.parsed_responses = [
            ConnectionClosedError(
                endpoint_url='https://ec2.us-east-1.amazonaws.com/'
            ),
            vpc_response('vpc-2'),
        ]
        stdout, stderr, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1',
            expected_rc=GENERAL_ERROR_RC,
        )
        self.assertEqual(stdout, '')
        self.assertEqual(self.called_regions, ['us-east-1'])
        self.assertIn('[us-east-1] Connection was closed', stderr)

    def test_no_incomplete_results_warning_once_the_command_fails(self):
        self.parsed_responses = [
            {'Vpcs': [{'VpcId': 'vpc-1'}], 'NextToken': 'more'},
            {'Error': {'Code': 'AccessDenied', 'Message': 'denied'}},
        ]
        _, stderr, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '
            '--no-paginate',
            expected_rc=CLIENT_ERROR_RC,
        )
        self.assertNotIn('incomplete', stderr)

    def test_text_has_already_printed_the_earlier_regions(self):
        # Like the pages of a single region, each region is printed as it
        # finishes, so a later failure leaves the earlier output in place.
        self.parsed_responses = [
            vpc_response('vpc-1'),
            {'Error': {'Code': 'AccessDenied', 'Message': 'denied'}},
            vpc_response('vpc-3'),
        ]
        stdout, stderr, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1,ap-south-1 '
            '--output text',
            expected_rc=CLIENT_ERROR_RC,
        )
        self.assertIn('vpc-1', stdout)
        self.assertNotIn('vpc-3', stdout)
        self.assertEqual(self.called_regions, ['us-east-1', 'eu-west-1'])
        self.assertIn(
            'aws: [ERROR]: [eu-west-1] An error occurred (AccessDenied)',
            stderr,
        )

    def test_structured_error_format_names_the_region(self):
        self.parsed_responses = [
            {'Error': {'Code': 'AccessDenied', 'Message': 'denied'}},
        ]
        _, stderr, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '
            '--cli-error-format json',
            expected_rc=CLIENT_ERROR_RC,
        )
        self.assertEqual(
            json.loads(stderr),
            {'Code': 'AccessDenied', 'Message': '[us-east-1] denied'},
        )

    def test_yaml_stream_has_already_printed_the_earlier_regions(self):
        self.parsed_responses = [
            vpc_response('vpc-1'),
            {'Error': {'Code': 'AccessDenied', 'Message': 'denied'}},
            vpc_response('vpc-3'),
        ]
        stdout, stderr, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1,ap-south-1 '
            '--output yaml-stream',
            expected_rc=CLIENT_ERROR_RC,
        )
        self.assertIn('vpc-1', stdout)
        self.assertNotIn('vpc-3', stdout)
        self.assertEqual(self.called_regions, ['us-east-1', 'eu-west-1'])
        self.assertIn('[eu-west-1] An error occurred (AccessDenied)', stderr)


class TestMultiRegionValidation(BaseMultiRegionTest):
    def assert_rejected(
        self, cmd, message, expected_rc=PARAM_VALIDATION_ERROR_RC
    ):
        _, stderr, _ = self.run_cmd(cmd, expected_rc=expected_rc)
        self.assertIn(message, stderr)
        self.assertEqual(self.request_urls, [])

    def test_region_cannot_be_combined(self):
        self.assert_rejected(
            'ec2 describe-vpcs --region us-east-1 '
            '--multi-regions eu-west-1,eu-central-1',
            '--region cannot be used together with --multi-regions.',
        )

    def test_endpoint_url_cannot_be_combined(self):
        self.assert_rejected(
            'ec2 describe-vpcs --endpoint-url https://localhost '
            '--multi-regions eu-west-1',
            '--endpoint-url cannot be used together with --multi-regions.',
        )

    def test_regions_must_be_in_one_partition(self):
        self.assert_rejected(
            'ec2 describe-vpcs --multi-regions us-east-1,cn-north-1',
            'all regions must be in the same partition (us-east-1 is in '
            '"aws", cn-north-1 is in "aws-cn")',
        )

    def test_malformed_region_is_rejected(self):
        self.assert_rejected(
            'ec2 describe-vpcs --multi-regions not-a-region',
            '--multi-regions: "not-a-region" is not a valid region name.',
        )

    def test_empty_region_is_rejected(self):
        self.assert_rejected(
            ['ec2', 'describe-vpcs', '--multi-regions', 'us-east-1,'],
            'the region list has an empty entry',
        )

    def test_all_cannot_be_mixed_with_region_names(self):
        self.assert_rejected(
            'ec2 describe-vpcs --multi-regions all,us-east-1',
            '"all" cannot be combined with explicit region names.',
        )

    def test_customization_command_is_rejected(self):
        # A customization command never has the option added, so the
        # argument parser rejects it like any unknown option.
        self.assert_rejected(
            'logs tail my-group --multi-regions us-east-1,eu-west-1',
            'Unknown options: --multi-regions, us-east-1,eu-west-1',
        )

    def test_single_region_starting_token_is_rejected(self):
        self.assert_rejected(
            'ec2 describe-vpcs --starting-token abc123 '
            '--multi-regions us-east-1,eu-west-1',
            '--starting-token is not a token returned by a command run '
            'with --multi-regions.',
        )

    def test_native_pagination_token_is_rejected(self):
        self.assert_rejected(
            'ec2 describe-vpcs --next-token abc123 '
            '--multi-regions us-east-1,eu-west-1',
            'cannot be used together with --multi-regions',
        )

    def test_output_skeleton_is_merged_like_real_output(self):
        # Each region's stubbed response is labelled and merged, so the
        # skeleton has the shape of a real multi-region response.
        stdout, stderr, _ = self.run_cmd(
            [
                'ec2',
                'describe-vpcs',
                '--generate-cli-skeleton',
                'output',
                '--multi-regions',
                'us-east-1,eu-west-1',
                '--query',
                '{Regions: Vpcs[]._CliScope.Region, NextToken: NextToken}',
            ]
        )
        self.assertEqual(
            json.loads(stdout),
            {'Regions': ['us-east-1', 'eu-west-1'], 'NextToken': 'NextToken'},
        )
        # The placeholder tokens are not reported as truncated results.
        self.assertEqual(stderr, '')

    def test_output_skeleton_does_not_resolve_credentials(self):
        # Like a single-region skeleton, it is generated without credentials.
        credentials = mock.Mock()
        credentials.get_frozen_credentials.side_effect = (
            UnauthorizedSSOTokenError()
        )
        with mock.patch.object(
            self.driver.session, 'get_credentials', return_value=credentials
        ):
            self.run_cmd(
                'ec2 describe-vpcs --generate-cli-skeleton output '
                '--multi-regions us-east-1,eu-west-1'
            )
        credentials.get_frozen_credentials.assert_not_called()

    def test_output_skeleton_with_all_makes_no_call(self):
        # Every region with an ec2 endpoint stands in for the enabled
        # regions, so the account is not asked for its regions.
        stdout, _, _ = self.run_cmd(
            [
                'ec2',
                'describe-vpcs',
                '--generate-cli-skeleton',
                'output',
                '--multi-regions',
                'all',
                '--query',
                'Vpcs[]._CliScope.Region',
            ]
        )
        regions = json.loads(stdout)
        self.assertEqual(
            regions, sorted(self.driver.session.get_available_regions('ec2'))
        )
        self.assertNotIn(
            'ListRegions',
            [model.name for model, _ in self.operations_called],
        )

    def test_input_skeleton_is_allowed(self):
        stdout, _, _ = self.run_cmd(
            'ec2 describe-vpcs --generate-cli-skeleton '
            '--multi-regions us-east-1,eu-west-1'
        )
        self.assertIn('VpcIds', stdout)
        self.assertEqual(self.request_urls, [])


class TestMultiRegionAll(BaseMultiRegionTest):
    def test_calls_every_enabled_region_the_service_is_in(self):
        self.parsed_responses = [
            {
                'Regions': [
                    {'RegionName': 'us-east-1'},
                    {'RegionName': 'eu-west-1'},
                    # A region the account has enabled but that is not in
                    # the endpoint data for ec2.
                    {'RegionName': 'us-west-42'},
                ]
            },
            vpc_response('vpc-eu-west-1'),
            vpc_response('vpc-us-east-1'),
        ]
        stdout, _, _ = self.run_cmd('ec2 describe-vpcs --multi-regions all')
        self.assertEqual(
            self.called_regions[0], 'us-east-1'
        )  # account list-regions
        self.assertEqual(self.operations_called[0][0].name, 'ListRegions')
        # Regions are called in alphabetical order for ``all``.
        self.assertEqual(self.called_regions[1:], ['eu-west-1', 'us-east-1'])
        self.assertEqual(
            [vpc['_CliScope']['Region'] for vpc in json.loads(stdout)['Vpcs']],
            ['eu-west-1', 'us-east-1'],
        )

    def test_falls_back_to_ec2_describe_regions(self):
        self.parsed_responses = [
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'denied'}},
            {
                'Regions': [
                    {'RegionName': 'eu-west-1', 'OptInStatus': 'opted-in'},
                    {
                        'RegionName': 'us-east-1',
                        'OptInStatus': 'opt-in-not-required',
                    },
                ]
            },
            vpc_response('vpc-eu-west-1'),
            vpc_response('vpc-us-east-1'),
        ]
        self.run_cmd('ec2 describe-vpcs --multi-regions all')
        self.assertEqual(
            [model.name for model, _ in self.operations_called],
            [
                'ListRegions',
                'DescribeRegions',
                'DescribeVpcs',
                'DescribeVpcs',
            ],
        )

    def test_fails_when_enabled_regions_cannot_be_listed(self):
        denied = {
            'Error': {'Code': 'AccessDeniedException', 'Message': 'denied'}
        }
        self.parsed_responses = [denied, denied]
        _, stderr, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions all',
            expected_rc=CONFIGURATION_ERROR_RC,
        )
        self.assertIn('could not determine which regions are enabled', stderr)
        self.assertEqual(
            [model.name for model, _ in self.operations_called],
            ['ListRegions', 'DescribeRegions'],
        )


class TestExistingParamsAreUnaffected(BaseMultiRegionTest):
    """The option must not shadow parameters commands already define.

    The global argument parser expands option prefixes, so a global
    ``--multi-regions`` would swallow the ``--multi-region`` parameter of
    the operations that model one.  Adding it per command instead leaves
    those parameters alone.
    """

    def test_kms_create_key_multi_region_param_still_works(self):
        self.parsed_responses = [{'KeyMetadata': {'KeyId': 'key-1'}}]
        self.run_cmd('kms create-key --multi-region')
        self.assertEqual(self.last_kwargs, {'MultiRegion': True})

    def test_kms_create_key_no_multi_region_param_still_works(self):
        self.parsed_responses = [{'KeyMetadata': {'KeyId': 'key-1'}}]
        self.run_cmd('kms create-key --no-multi-region')
        self.assertEqual(self.last_kwargs, {'MultiRegion': False})

    def test_ec2_provision_byoip_cidr_multi_region_param_still_works(self):
        self.parsed_responses = [{'ByoipCidr': {'Cidr': '10.0.0.0/24'}}]
        self.run_cmd(
            'ec2 provision-byoip-cidr --cidr 10.0.0.0/24 --multi-region'
        )
        self.assertEqual(
            self.last_kwargs, {'Cidr': '10.0.0.0/24', 'MultiRegion': True}
        )

    def test_operation_regions_param_still_works(self):
        self.parsed_responses = [{'DataLakes': []}]
        self.run_cmd('securitylake list-data-lakes --regions us-east-1')
        self.assertEqual(self.last_kwargs, {'regions': ['us-east-1']})


class TestOptionIsOfferedOnlyWhereSupported(BaseMultiRegionTest):
    def assert_in_arg_table(self, cmd, expected):
        service, operation = cmd.split()
        command = self.driver.subcommand_table[service].subcommand_table[
            operation
        ]
        self.assertEqual('multi-regions' in command.arg_table, expected)

    def test_added_to_an_eligible_command(self):
        self.assert_in_arg_table('ec2 describe-vpcs', True)
        self.assert_in_arg_table('lambda list-functions', True)

    def test_not_added_to_a_mutating_command(self):
        self.assert_in_arg_table('ec2 terminate-instances', False)
        self.assert_in_arg_table('kms create-key', False)

    def test_not_added_to_a_credential_command(self):
        self.assert_in_arg_table('sts get-session-token', False)
        self.assert_in_arg_table('ecr get-authorization-token', False)

    def test_not_added_to_a_global_service(self):
        self.assert_in_arg_table('iam list-users', False)
        self.assert_in_arg_table('organizations list-accounts', False)
        self.assert_in_arg_table('taxsettings list-tax-registrations', False)

    def test_not_added_to_a_data_plane_read(self):
        self.assert_in_arg_table('dynamodb scan', False)
        self.assert_in_arg_table('sqs receive-message', False)

    def test_not_added_when_the_response_cannot_be_merged(self):
        # A response that is a single structure or a set of scalars has
        # no merge that keeps every region's data.
        self.assert_in_arg_table('dynamodb describe-table', False)
        self.assert_in_arg_table('kms describe-key', False)
        self.assert_in_arg_table('secretsmanager describe-secret', False)

    def test_rejected_when_the_response_cannot_be_merged(self):
        _, stderr, _ = self.run_cmd(
            'dynamodb describe-table --table-name widgets '
            '--multi-regions us-east-1,eu-west-1',
            expected_rc=PARAM_VALIDATION_ERROR_RC,
        )
        self.assertIn('Unknown options: --multi-regions', stderr)
        self.assertEqual(self.request_urls, [])


class TestMultiRegionAliases(BaseMultiRegionTest):
    """An alias must not be able to smuggle the option past validation."""

    def setUp(self):
        super().setUp()
        self.files = FileCreator()
        alias_path = self.files.create_file(
            'alias',
            '[toplevel]\n'
            'myvpcs = ec2 describe-vpcs --multi-regions us-east-1,eu-west-1\n',
        )
        self.driver.alias_loader = AliasLoader(alias_path)

    def tearDown(self):
        self.files.remove_all()
        super().tearDown()

    def test_alias_runs_in_every_region(self):
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        stdout, _, _ = self.run_cmd('myvpcs')
        self.assertEqual(self.called_regions, ['us-east-1', 'eu-west-1'])
        self.assertEqual(len(json.loads(stdout)['Vpcs']), 2)

    def test_endpoint_url_outside_the_alias_is_still_rejected(self):
        _, stderr, _ = self.run_cmd(
            'myvpcs --endpoint-url https://localhost:9999',
            expected_rc=PARAM_VALIDATION_ERROR_RC,
        )
        self.assertIn(
            '--endpoint-url cannot be used together with --multi-regions',
            stderr,
        )
        self.assertEqual(self.request_urls, [])

    def test_region_outside_the_alias_is_still_rejected(self):
        _, stderr, _ = self.run_cmd(
            'myvpcs --region us-west-2', expected_rc=PARAM_VALIDATION_ERROR_RC
        )
        self.assertIn(
            '--region cannot be used together with --multi-regions', stderr
        )
        self.assertEqual(self.request_urls, [])


class TestMultiRegionHelp(BaseAWSHelpOutputTest):
    def test_eligible_command_documents_the_option(self):
        self.driver.main(['ec2', 'describe-vpcs', 'help'])
        self.assert_contains('--multi-regions')
        self.assert_contains('_CliScope')

    def test_ineligible_command_does_not_document_the_option(self):
        self.driver.main(['ec2', 'terminate-instances', 'help'])
        self.assert_not_contains('--multi-regions')

    def test_command_with_its_own_multi_region_param_is_unchanged(self):
        self.driver.main(['kms', 'create-key', 'help'])
        self.assert_contains('--multi-region')
        self.assert_not_contains('--multi-regions')

    def test_not_documented_as_a_global_option(self):
        # It is added per command, so it must not appear in the global
        # options that every command's help includes.
        self.driver.main(['help'])
        self.assert_not_contains('--multi-regions')


class TestTruncatedResults(BaseMultiRegionTest):
    """A dropped pagination token must not look like a complete answer."""

    def test_no_paginate_reports_the_region_that_had_more(self):
        self.parsed_responses = [
            {'Vpcs': [{'VpcId': 'vpc-1'}], 'NextToken': 'more-in-us-east-1'},
            {'Vpcs': [{'VpcId': 'vpc-2'}]},
        ]
        stdout, stderr, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '
            '--no-paginate'
        )
        response = json.loads(stdout)
        self.assertEqual(
            [vpc['VpcId'] for vpc in response['Vpcs']], ['vpc-1', 'vpc-2']
        )
        self.assertNotIn('NextToken', response)
        self.assertIn('[us-east-1] the results are incomplete', stderr)
        self.assertNotIn('[eu-west-1]', stderr)

    def test_complete_results_say_nothing(self):
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        _, stderr, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1'
        )
        self.assertEqual(stderr, '')

    def test_yaml_stream_prints_a_region_before_calling_the_next(self):
        # The second region fails in a way that stops the command; the
        # first region has already been printed by then.
        self.parsed_responses = [vpc_response('vpc-1'), NoCredentialsError()]
        stdout, _, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '
            '--output yaml-stream',
            expected_rc=CONFIGURATION_ERROR_RC,
        )
        self.assertIn('vpc-1', stdout)

    def test_yaml_stream_from_the_environment_streams_too(self):
        self.environ['AWS_DEFAULT_OUTPUT'] = 'yaml-stream'
        self.parsed_responses = [vpc_response('vpc-1'), NoCredentialsError()]
        stdout, _, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1',
            expected_rc=CONFIGURATION_ERROR_RC,
        )
        self.assertIn('vpc-1', stdout)

    def test_yaml_stream_stops_calling_regions_once_output_is_closed(self):
        # For example ``| head`` exiting after the first region.
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        with mock.patch(
            'awscli.formatter.YAMLDumper.dump', side_effect=BrokenPipeError
        ):
            self.run_cmd(
                'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '
                '--output yaml-stream'
            )
        self.assertEqual(self.called_regions, ['us-east-1'])

    def test_yaml_stream_strips_tokens_and_reports_truncation(self):
        self.parsed_responses = [
            {'Vpcs': [{'VpcId': 'vpc-1'}], 'NextToken': 'more-in-us-east-1'},
            {'Vpcs': [{'VpcId': 'vpc-2'}]},
        ]
        stdout, stderr, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '
            '--no-paginate --output yaml-stream'
        )
        self.assertIn('vpc-1', stdout)
        self.assertIn('vpc-2', stdout)
        self.assertNotIn('NextToken', stdout)
        self.assertIn('[us-east-1] the results are incomplete', stderr)


class TestErrorClassification(BaseMultiRegionTest):
    """A failure is reported once per region, or once in total.

    A request that every region would reject the same way must be
    reported once, with the return code single region mode would use. A
    failure that belongs to one region is reported against that region
    and must not hide the regions that worked.
    """

    def test_parameter_validation_is_reported_as_in_one_region(self):
        # The parameters are the same in every region, so a malformed
        # parameter is a single failure, not one per region.
        multi_stdout, multi_stderr, _ = self.run_cmd(
            'ec2 describe-vpcs --filters NotAKey=value '
            '--multi-regions us-east-1,eu-west-1',
            expected_rc=PARAM_VALIDATION_ERROR_RC,
        )
        attempts = len(self.operations_called)
        single_stdout, single_stderr, _ = self.run_cmd(
            'ec2 describe-vpcs --filters NotAKey=value --region us-east-1',
            expected_rc=PARAM_VALIDATION_ERROR_RC,
        )
        self.assertEqual(multi_stderr, single_stderr)
        self.assertEqual(multi_stdout, single_stdout)
        self.assertIn(
            'Unknown parameter in Filters[0]: "NotAKey"', multi_stderr
        )
        # The second region is never attempted: validation happens while
        # the first region's request is being serialized.
        self.assertEqual(attempts, 1)
        self.assertEqual(self.request_urls, [])

    def test_missing_credentials_is_reported_once(self):
        # Credentials are resolved once for the whole command, so the
        # same failure would be repeated by every region.
        self.parsed_responses = [NoCredentialsError()]
        stdout, stderr, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1',
            expected_rc=CONFIGURATION_ERROR_RC,
        )
        self.assertEqual(stdout, '')
        self.assertEqual(stderr.count('Unable to locate credentials'), 1)
        self.assertNotIn('[eu-west-1]', stderr)
        # Only the first region is attempted.
        self.assertEqual(self.called_regions, ['us-east-1'])

    def test_no_credentials_up_front_is_left_to_each_region(self):
        # Without credentials there is nothing to resolve up front; the
        # region calls report it (see the test above).
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        with mock.patch.object(
            self.driver.session, 'get_credentials', return_value=None
        ):
            self.run_cmd(
                'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1'
            )
        self.assertEqual(self.called_regions, ['us-east-1', 'eu-west-1'])

    def test_expired_sso_session_is_reported_once(self):
        # Refreshable credentials fail when they are first used, not when
        # the session is created.
        credentials = mock.Mock()
        credentials.get_frozen_credentials.side_effect = (
            UnauthorizedSSOTokenError()
        )
        with mock.patch.object(
            self.driver.session, 'get_credentials', return_value=credentials
        ):
            stdout, stderr, _ = self.run_cmd(
                'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1',
                expected_rc=GENERAL_ERROR_RC,
            )
        self.assertEqual(stdout, '')
        self.assertEqual(stderr.count(str(UnauthorizedSSOTokenError())), 1)
        self.assertNotIn('[us-east-1]', stderr)
        self.assertEqual(self.request_urls, [])


class TestRegionsWithoutAnEndpoint(BaseMultiRegionTest):
    """``all`` must not report regions a service was never launched in.

    The built-in endpoint data lists no regions for some services, so
    ``all`` calls every enabled region and treats a hostname that does
    not resolve as "the service is not here".
    """

    def setUp(self):
        super().setUp()
        self.assertEqual(
            self.driver.session.get_available_regions(
                SERVICE_WITHOUT_ENDPOINTS, 'aws'
            ),
            [],
            f'{SERVICE_WITHOUT_ENDPOINTS} now has endpoint data, so it no '
            'longer exercises the region skipping behaviour',
        )

    def enabled_regions(self, *names):
        return {'Regions': [{'RegionName': name} for name in names]}

    def test_region_without_an_endpoint_is_left_out(self):
        self.parsed_responses = [
            self.enabled_regions('us-east-1', 'eu-west-1'),
            name_resolution_failure('https://dsql.eu-west-1.api.aws/cluster'),
            {'clusters': [{'identifier': 'cluster-us-east-1'}]},
        ]
        stdout, stderr, _ = self.run_cmd(
            'dsql list-clusters --multi-regions all'
        )
        self.assertEqual(
            json.loads(stdout),
            {
                'clusters': [
                    {
                        'identifier': 'cluster-us-east-1',
                        '_CliScope': {'Region': 'us-east-1'},
                    }
                ]
            },
        )
        # A region the service was never launched in is not an error.
        self.assertEqual(stderr, '')
        self.assertEqual(
            self.called_regions, ['us-east-1', 'eu-west-1', 'us-east-1']
        )

    def test_every_region_without_an_endpoint_is_reported(self):
        self.parsed_responses = [
            self.enabled_regions('us-east-1', 'eu-west-1'),
            name_resolution_failure('https://dsql.eu-west-1.api.aws/cluster'),
            name_resolution_failure('https://dsql.us-east-1.api.aws/cluster'),
        ]
        stdout, stderr, _ = self.run_cmd(
            'dsql list-clusters --multi-regions all',
            expected_rc=GENERAL_ERROR_RC,
        )
        self.assertEqual(stdout, '')
        self.assertIn(
            '[eu-west-1, us-east-1] could not resolve any endpoint', stderr
        )

    def test_resumed_listing_ending_in_regions_without_an_endpoint(self):
        # The first page ends at the last region that has the service, so
        # its token resumes only in regions that do not; the listing is
        # complete rather than a network failure.
        self.parsed_responses = [
            self.enabled_regions('us-east-1', 'eu-west-1'),
            {'clusters': [{'identifier': 'cluster-eu-west-1'}]},
        ]
        stdout, _, _ = self.run_cmd(
            'dsql list-clusters --multi-regions all --max-items 1'
        )
        token = json.loads(stdout)['NextToken']

        self.request_urls = []
        self.parsed_responses = [
            self.enabled_regions('us-east-1', 'eu-west-1'),
            name_resolution_failure('https://dsql.us-east-1.api.aws/cluster'),
        ]
        stdout, stderr, _ = self.run_cmd(
            f'dsql list-clusters --multi-regions all --starting-token {token}'
        )
        self.assertEqual(stdout, '')
        self.assertNotIn('could not resolve any endpoint', stderr)

    def test_region_named_on_the_command_line_is_never_skipped(self):
        # The user asked for this region by name, so a hostname that does
        # not resolve is reported instead of being passed over.
        self.parsed_responses = [
            name_resolution_failure('https://dsql.eu-west-1.api.aws/cluster'),
            {'clusters': [{'identifier': 'cluster-us-east-1'}]},
        ]
        stdout, stderr, _ = self.run_cmd(
            'dsql list-clusters --multi-regions eu-west-1,us-east-1',
            expected_rc=GENERAL_ERROR_RC,
        )
        self.assertEqual(stdout, '')
        self.assertEqual(self.called_regions, ['eu-west-1'])
        self.assertIn('[eu-west-1] Could not connect to the endpoint', stderr)
        self.assertNotIn('could not resolve any endpoint', stderr)


class TestPaginationTokensAreStripped(BaseMultiRegionTest):
    """A token belongs to one region, so it cannot be merged.

    The token names come from the shipped paginator models, which is why
    a service that calls its token something other than ``NextToken`` is
    handled too.
    """

    def test_marker_tokens_are_stripped(self):
        # efs describe-file-systems pages with Marker/NextMarker and
        # echoes the Marker it was called with.
        self.parsed_responses = [
            {
                'FileSystems': [{'FileSystemId': 'fs-us-east-1'}],
                'Marker': 'echoed-marker',
                'NextMarker': 'more-in-us-east-1',
            },
            {'FileSystems': [{'FileSystemId': 'fs-eu-west-1'}]},
        ]
        stdout, stderr, _ = self.run_cmd(
            'efs describe-file-systems --multi-regions us-east-1,eu-west-1 '
            '--no-paginate'
        )
        response = json.loads(stdout)
        self.assertEqual(
            [item['FileSystemId'] for item in response['FileSystems']],
            ['fs-us-east-1', 'fs-eu-west-1'],
        )
        self.assertEqual(list(response), ['FileSystems'])
        self.assertIn('[us-east-1] the results are incomplete', stderr)

    def test_token_that_is_not_called_next_token_is_stripped(self):
        # apigateway get-rest-apis calls its pagination token "position".
        self.parsed_responses = [
            {'items': [{'id': 'api-us-east-1'}], 'position': 'more'},
            {'items': [{'id': 'api-eu-west-1'}]},
        ]
        stdout, stderr, _ = self.run_cmd(
            'apigateway get-rest-apis --multi-regions us-east-1,eu-west-1 '
            '--no-paginate'
        )
        response = json.loads(stdout)
        self.assertEqual(
            [item['id'] for item in response['items']],
            ['api-us-east-1', 'api-eu-west-1'],
        )
        self.assertNotIn('position', response)
        self.assertIn('[us-east-1] the results are incomplete', stderr)

    def test_single_region_still_returns_the_token(self):
        # Without --multi-regions the token is the user's way to resume,
        # so it must still be there.
        self.parsed_responses = [
            {'items': [{'id': 'api-us-east-1'}], 'position': 'more'}
        ]
        stdout, stderr, _ = self.run_cmd(
            'apigateway get-rest-apis --region us-east-1 --no-paginate'
        )
        self.assertEqual(json.loads(stdout)['position'], 'more')
        self.assertEqual(stderr, '')


class TestCommandsThatOptOut(BaseMultiRegionTest):
    """Commands that do more than call an operation and print it."""

    def arg_table(self, *path):
        command = self.driver
        for name in path:
            command = command.subcommand_table[name]
        return command.arg_table

    def test_option_is_absent_from_a_waiter(self):
        # A waiter polls one region until it reaches a state.
        self.assertNotIn(
            'multi-regions', self.arg_table('ecs', 'wait', 'services-stable')
        )

    def test_waiter_command_is_rejected(self):
        _, stderr, _ = self.run_cmd(
            'ecs wait services-stable --services my-service '
            '--multi-regions us-east-1,eu-west-1',
            expected_rc=PARAM_VALIDATION_ERROR_RC,
        )
        self.assertIn('Unknown options: --multi-regions', stderr)
        self.assertEqual(self.request_urls, [])

    def test_start_session_is_rejected(self):
        _, stderr, _ = self.run_cmd(
            'ssm start-session --target i-0abc1234 '
            '--multi-regions us-east-1,eu-west-1',
            expected_rc=PARAM_VALIDATION_ERROR_RC,
        )
        self.assertIn(
            'Unknown options: --multi-regions, us-east-1,eu-west-1', stderr
        )
        self.assertEqual(self.request_urls, [])

    def test_execute_command_is_rejected(self):
        _, stderr, _ = self.run_cmd(
            'ecs execute-command --task task-1 --command /bin/sh '
            '--interactive --multi-regions us-east-1,eu-west-1',
            expected_rc=PARAM_VALIDATION_ERROR_RC,
        )
        self.assertIn(
            'Unknown options: --multi-regions, us-east-1,eu-west-1', stderr
        )
        self.assertEqual(self.request_urls, [])


class TestConfiguredEndpointUrl(BaseMultiRegionTest):
    """One endpoint for every region cannot be what the user meant.

    ``--endpoint-url`` is rejected by validation, but the same thing can
    be configured out of band, in which case every region would be sent
    to that one endpoint and the identical responses would be labelled
    with different regions.
    """

    def assert_rejected(self):
        _, stderr, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1',
            expected_rc=PARAM_VALIDATION_ERROR_RC,
        )
        self.assertIn('https://localhost:9999', stderr)
        self.assertIn('--multi-regions', stderr)
        self.assertEqual(self.request_urls, [])
        self.assertEqual(self.operations_called, [])

    def test_global_endpoint_url_variable_is_rejected(self):
        self.environ['AWS_ENDPOINT_URL'] = 'https://localhost:9999'
        self.assert_rejected()

    def test_service_endpoint_url_variable_is_rejected(self):
        self.environ['AWS_ENDPOINT_URL_EC2'] = 'https://localhost:9999'
        self.assert_rejected()

    def test_endpoint_url_of_the_first_region_is_rejected(self):
        # Still one endpoint for every region, even though it is the
        # first region's own.
        self.environ['AWS_ENDPOINT_URL_EC2'] = (
            'https://ec2.us-east-1.amazonaws.com'
        )
        _, stderr, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1',
            expected_rc=PARAM_VALIDATION_ERROR_RC,
        )
        self.assertIn('A configured endpoint URL cannot be used', stderr)
        self.assertEqual(self.request_urls, [])

    def test_ignored_endpoint_url_runs_in_every_region(self):
        self.environ['AWS_ENDPOINT_URL'] = 'https://localhost:9999'
        self.environ['AWS_IGNORE_CONFIGURED_ENDPOINT_URLS'] = 'true'
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        self.run_cmd('ec2 describe-vpcs --multi-regions us-east-1,eu-west-1')
        self.assertEqual(self.called_regions, ['us-east-1', 'eu-west-1'])

    def test_endpoint_url_variable_is_honoured_for_one_region(self):
        # The variable really does redirect the command, which is why it
        # has to be rejected above.
        self.environ['AWS_ENDPOINT_URL'] = 'https://localhost:9999'
        self.parsed_responses = [vpc_response('vpc-1')]
        self.run_cmd('ec2 describe-vpcs --region us-east-1')
        self.assertEqual(self.request_urls, ['https://localhost:9999/'])

    def test_output_skeleton_is_not_rejected(self):
        # Like a single-region skeleton, it sends no request.
        self.environ['AWS_ENDPOINT_URL'] = 'https://localhost:9999'
        stdout, _, _ = self.run_cmd(
            'ec2 describe-vpcs --generate-cli-skeleton output '
            '--multi-regions us-east-1,eu-west-1'
        )
        self.assertIn('_CliScope', stdout)
        self.assertEqual(self.request_urls, [])

    def test_endpoint_url_for_another_service_is_not_rejected(self):
        self.environ['AWS_ENDPOINT_URL_DYNAMODB'] = 'https://localhost:9999'
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        self.run_cmd('ec2 describe-vpcs --multi-regions us-east-1,eu-west-1')
        self.assertEqual(self.called_regions, ['us-east-1', 'eu-west-1'])

    def test_no_configured_endpoint_url_runs_in_every_region(self):
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        self.run_cmd('ec2 describe-vpcs --multi-regions us-east-1,eu-west-1')
        self.assertEqual(
            self.request_urls,
            [
                'https://ec2.us-east-1.amazonaws.com/',
                'https://ec2.eu-west-1.amazonaws.com/',
            ],
        )


class TestEndpointUrlInConfigFile(BaseMultiRegionTest):
    def setUp(self):
        super().setUp()
        self.files = FileCreator()
        self.addCleanup(self.files.remove_all)
        self.environ['AWS_CONFIG_FILE'] = self.files.create_file(
            'config', '[default]\nendpoint_url = https://localhost:9999\n'
        )
        self.driver = create_clidriver()
        self.entry_point = AWSCLIEntryPoint(self.driver)

    def test_endpoint_url_setting_is_rejected(self):
        _, stderr, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1',
            expected_rc=PARAM_VALIDATION_ERROR_RC,
        )
        self.assertIn('https://localhost:9999', stderr)
        self.assertEqual(self.request_urls, [])

    def test_endpoint_url_setting_is_honoured_for_one_region(self):
        self.parsed_responses = [vpc_response('vpc-1')]
        self.run_cmd('ec2 describe-vpcs --region us-east-1')
        self.assertEqual(self.request_urls, ['https://localhost:9999/'])


class TestOtherOptions(BaseMultiRegionTest):
    """Options a command already supports keep working per region."""

    def test_cli_input_json_is_sent_to_every_region(self):
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        self.run_cmd(
            [
                'ec2',
                'describe-vpcs',
                '--cli-input-json',
                '{"VpcIds": ["vpc-1", "vpc-2"]}',
                '--multi-regions',
                'us-east-1,eu-west-1',
            ]
        )
        self.assertEqual(
            [params for _, params in self.operations_called],
            [
                {'VpcIds': ['vpc-1', 'vpc-2']},
                {'VpcIds': ['vpc-1', 'vpc-2']},
            ],
        )

    def test_cli_input_json_pagination_token_is_rejected(self):
        _, stderr, _ = self.run_cmd(
            [
                'ec2',
                'describe-vpcs',
                '--cli-input-json',
                '{"NextToken": "abc123"}',
                '--multi-regions',
                'us-east-1,eu-west-1',
            ],
            expected_rc=PARAM_VALIDATION_ERROR_RC,
        )
        self.assertIn(
            'NextToken cannot be used together with --multi-regions', stderr
        )
        self.assertEqual(self.request_urls, [])

    def test_generate_cli_skeleton_is_printed_once(self):
        stdout, _, _ = self.run_cmd(
            'ec2 describe-vpcs --generate-cli-skeleton '
            '--multi-regions us-east-1,eu-west-1'
        )
        # One skeleton, not one per region.
        skeleton = json.loads(stdout)
        self.assertEqual(skeleton['VpcIds'], [''])
        self.assertEqual(stdout.count('"VpcIds"'), 1)
        self.assertEqual(self.request_urls, [])

    def test_page_size_is_sent_to_every_region(self):
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '
            '--page-size 5'
        )
        self.assertEqual(
            [params for _, params in self.operations_called],
            [{'MaxResults': 5}, {'MaxResults': 5}],
        )

    def test_ec2_page_size_injector_applies_to_every_region(self):
        # ec2 describe-volumes pages with a larger page size by default;
        # its calling-command handler still runs.
        self.parsed_responses = [{'Volumes': []}, {'Volumes': []}]
        self.run_cmd(
            'ec2 describe-volumes --multi-regions us-east-1,eu-west-1'
        )
        self.assertEqual(
            [params for _, params in self.operations_called],
            [{'MaxResults': 1000}, {'MaxResults': 1000}],
        )

    def test_command_lineage_is_in_the_user_agent_of_every_region(self):
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        self.run_cmd('ec2 describe-vpcs --multi-regions us-east-1,eu-west-1')
        self.assertEqual(len(self.user_agents), 2)
        for user_agent in self.user_agents:
            self.assertIn('md/command#ec2.describe-vpcs', user_agent)

    def run_page(self, cmd, responses):
        self.parsed_responses = responses
        self.request_urls = []
        stdout, stderr, _ = self.run_cmd(cmd)
        self.assertEqual(stderr, '')
        result = json.loads(stdout)
        items = [
            (vpc['VpcId'], vpc['_CliScope']['Region'])
            for vpc in result['Vpcs']
        ]
        # The regions called, in order.  The test harness answers a call
        # with a starting token twice, with or without --multi-regions.
        called = list(dict.fromkeys(self.called_regions))
        return items, result.get('NextToken'), called

    def test_max_items_limits_the_whole_command(self):
        # The second region is only asked for what the first one left.
        items, token, called = self.run_page(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '
            '--max-items 3',
            [
                {'Vpcs': [{'VpcId': 'vpc-1'}, {'VpcId': 'vpc-2'}]},
                {'Vpcs': [{'VpcId': 'vpc-3'}, {'VpcId': 'vpc-4'}]},
            ],
        )
        self.assertEqual(
            items,
            [
                ('vpc-1', 'us-east-1'),
                ('vpc-2', 'us-east-1'),
                ('vpc-3', 'eu-west-1'),
            ],
        )
        self.assertIsNotNone(token)

    def test_regions_after_max_items_is_reached_are_not_called(self):
        items, token, called = self.run_page(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1,ap-south-1 '
            '--max-items 1',
            [{'Vpcs': [{'VpcId': 'vpc-1'}, {'VpcId': 'vpc-2'}]}],
        )
        self.assertEqual(items, [('vpc-1', 'us-east-1')])
        self.assertEqual(called, ['us-east-1'])
        self.assertIsNotNone(token)

    def test_starting_token_pages_through_every_region(self):
        # Paging with the returned token loses nothing, as with a single
        # region: each page resumes where the previous one stopped.
        cmd = 'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '

        # botocore truncates the pages it is given, so each run gets its
        # own copy.
        def us_east():
            return {'Vpcs': [{'VpcId': 'vpc-1'}, {'VpcId': 'vpc-2'}]}

        def eu_west():
            return {'Vpcs': [{'VpcId': 'vpc-3'}, {'VpcId': 'vpc-4'}]}

        first, token, called = self.run_page(
            cmd + '--max-items 1', [us_east()]
        )
        self.assertEqual(first, [('vpc-1', 'us-east-1')])
        self.assertEqual(called, ['us-east-1'])

        second, token, called = self.run_page(
            cmd + f'--max-items 2 --starting-token {token}',
            [us_east(), eu_west()],
        )
        self.assertEqual(
            second, [('vpc-2', 'us-east-1'), ('vpc-3', 'eu-west-1')]
        )
        self.assertEqual(called, ['us-east-1', 'eu-west-1'])

        last, token, called = self.run_page(
            cmd + f'--starting-token {token}', [eu_west()]
        )
        self.assertEqual(last, [('vpc-4', 'eu-west-1')])
        self.assertEqual(called, ['eu-west-1'])
        self.assertIsNone(token)

    def test_token_ending_at_a_region_boundary_resumes_in_the_next(self):
        cmd = 'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '
        _, token, _ = self.run_page(
            cmd + '--max-items 1', [vpc_response('vpc-1')]
        )
        items, token, called = self.run_page(
            cmd + f'--starting-token {token}', [vpc_response('vpc-2')]
        )
        self.assertEqual(items, [('vpc-2', 'eu-west-1')])
        self.assertEqual(called, ['eu-west-1'])
        self.assertIsNone(token)

    def test_token_for_a_region_not_listed_is_rejected(self):
        _, token, _ = self.run_page(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '
            '--max-items 1',
            [{'Vpcs': [{'VpcId': 'vpc-1'}, {'VpcId': 'vpc-2'}]}],
        )
        _, stderr, _ = self.run_cmd(
            f'ec2 describe-vpcs --multi-regions eu-west-1 '
            f'--starting-token {token}',
            expected_rc=PARAM_VALIDATION_ERROR_RC,
        )
        self.assertIn('resumes in us-east-1, which is not one of', stderr)

    def test_text_prints_the_token_like_a_single_region(self):
        self.parsed_responses = [
            {'Vpcs': [{'VpcId': 'vpc-1'}, {'VpcId': 'vpc-2'}]}
        ]
        stdout, _, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '
            '--max-items 1 --output text'
        )
        self.assertIn('vpc-1', stdout)
        self.assertRegex(stdout, r'NEXTTOKEN\t\S+')

    def test_yaml_stream_omits_the_token_like_a_single_region(self):
        self.parsed_responses = [
            {'Vpcs': [{'VpcId': 'vpc-1'}, {'VpcId': 'vpc-2'}]}
        ]
        stdout, _, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '
            '--max-items 1 --output yaml-stream'
        )
        self.assertIn('vpc-1', stdout)
        self.assertNotIn('NextToken', stdout)

    def test_max_items_with_a_string_limit_key(self):
        # apigatewayv2 models its page size as a string, so --max-items
        # is parsed as one too.
        self.parsed_responses = [
            {'Items': [{'ApiId': 'api-1'}, {'ApiId': 'api-2'}]}
        ]
        stdout, _, _ = self.run_cmd(
            'apigatewayv2 get-apis --multi-regions us-east-1,eu-west-1 '
            '--max-items 1'
        )
        result = json.loads(stdout)
        self.assertEqual([api['ApiId'] for api in result['Items']], ['api-1'])
        self.assertIn('NextToken', result)

    def test_debug_still_prints_the_merged_response(self):
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        stdout, _, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 --debug'
        )
        self.assertEqual(
            [vpc['_CliScope']['Region'] for vpc in json.loads(stdout)['Vpcs']],
            ['us-east-1', 'eu-west-1'],
        )

    def test_no_sign_request_applies_to_every_region(self):
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '
            '--no-sign-request'
        )
        self.assertEqual(self.called_regions, ['us-east-1', 'eu-west-1'])
        self.assertEqual(self.signature_versions, [UNSIGNED, UNSIGNED])

    def test_no_sign_request_does_not_resolve_credentials(self):
        # An expired SSO session must not stop an anonymous request.
        credentials = mock.Mock()
        credentials.get_frozen_credentials.side_effect = (
            UnauthorizedSSOTokenError()
        )
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        with mock.patch.object(
            self.driver.session, 'get_credentials', return_value=credentials
        ):
            self.run_cmd(
                'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '
                '--no-sign-request'
            )
        self.assertEqual(self.called_regions, ['us-east-1', 'eu-west-1'])
        credentials.get_frozen_credentials.assert_not_called()

    def test_requests_are_signed_without_that_option(self):
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        self.run_cmd('ec2 describe-vpcs --multi-regions us-east-1,eu-west-1')
        self.assertNotIn(UNSIGNED, self.signature_versions)
        self.assertEqual(len(self.signature_versions), 2)

    def test_color_off_leaves_the_output_unstyled(self):
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        stdout, _, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '
            '--output table --color off'
        )
        self.assertNotIn('\x1b[', stdout)
        self.assertIn('us-east-1', stdout)
        self.assertIn('eu-west-1', stdout)

    def test_color_on_styles_the_output(self):
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        stdout, _, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '
            '--output table --color on'
        )
        self.assertIn('\x1b[', stdout)
        self.assertIn('us-east-1', stdout)

    def test_query_with_text_output(self):
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        stdout, _, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '
            '--query Vpcs[].[VpcId,_CliScope.Region] --output text'
        )
        self.assertEqual(stdout, 'vpc-1\tus-east-1\nvpc-2\teu-west-1\n')


class TestProfile(BaseMultiRegionTest):
    """The regions come from the option, everything else from the profile."""

    def setUp(self):
        super().setUp()
        self.files = FileCreator()
        self.addCleanup(self.files.remove_all)
        self.environ['AWS_CONFIG_FILE'] = self.files.create_file(
            'config', '[profile elsewhere]\nregion = ap-northeast-1\n'
        )
        self.environ['AWS_SHARED_CREDENTIALS_FILE'] = self.files.create_file(
            'credentials',
            '[elsewhere]\n'
            'aws_access_key_id = profile_key\n'
            'aws_secret_access_key = profile_secret\n',
        )
        del self.environ['AWS_ACCESS_KEY_ID']
        del self.environ['AWS_SECRET_ACCESS_KEY']
        del self.environ['AWS_DEFAULT_REGION']
        self.driver = create_clidriver()
        self.entry_point = AWSCLIEntryPoint(self.driver)

    def test_profile_region_is_used_without_the_option(self):
        self.parsed_responses = [vpc_response('vpc-1')]
        self.run_cmd('ec2 describe-vpcs --profile elsewhere')
        self.assertEqual(self.called_regions, ['ap-northeast-1'])

    def test_profile_region_is_not_called_with_the_option(self):
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        self.run_cmd(
            'ec2 describe-vpcs --profile elsewhere '
            '--multi-regions us-east-1,eu-west-1'
        )
        self.assertEqual(self.called_regions, ['us-east-1', 'eu-west-1'])

    def test_credentials_are_resolved_once_for_every_region(self):
        # One command, one set of credentials: a client is created per
        # region, but they all come from the same session.
        resolutions = []
        load_credentials = CredentialResolver.load_credentials

        def record(resolver):
            resolutions.append(resolver)
            return load_credentials(resolver)

        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        with mock.patch.object(CredentialResolver, 'load_credentials', record):
            self.run_cmd(
                'ec2 describe-vpcs --profile elsewhere '
                '--multi-regions us-east-1,eu-west-1'
            )
        self.assertEqual(self.called_regions, ['us-east-1', 'eu-west-1'])
        self.assertEqual(len(resolutions), 1)
        self.assertEqual(
            self.driver.session.get_credentials().access_key, 'profile_key'
        )


class TestQueryParity(BaseMultiRegionTest):
    """The same ``--query`` must work with and without the option.

    The merged response keeps the member names and the member types of a
    single region's response, so a query written for one region returns
    the same kind of result for several.
    """

    def test_top_level_list_query(self):
        self.parsed_responses = [vpc_response('vpc-1')]
        single, _, _ = self.run_cmd(
            'ec2 describe-vpcs --region us-east-1 --query Vpcs[].VpcId'
        )
        self.parsed_responses = [vpc_response('vpc-1'), vpc_response('vpc-2')]
        merged, _, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '
            '--query Vpcs[].VpcId'
        )
        self.assertEqual(json.loads(single), ['vpc-1'])
        self.assertEqual(json.loads(merged), ['vpc-1', 'vpc-2'])

    def test_nested_list_query(self):
        def reservation(instance_id):
            return {
                'Reservations': [
                    {
                        'ReservationId': f'r-{instance_id}',
                        'Instances': [{'InstanceId': instance_id}],
                    }
                ]
            }

        query = '--query Reservations[].Instances[].InstanceId'
        self.parsed_responses = [reservation('i-1')]
        single, _, _ = self.run_cmd(
            f'ec2 describe-instances --region us-east-1 {query}'
        )
        self.parsed_responses = [reservation('i-1'), reservation('i-2')]
        merged, _, _ = self.run_cmd(
            'ec2 describe-instances --multi-regions us-east-1,eu-west-1 '
            f'{query}'
        )
        self.assertEqual(json.loads(single), ['i-1'])
        self.assertEqual(json.loads(merged), ['i-1', 'i-2'])

    def test_query_sees_every_region_in_every_output_format(self):
        # Applied to each region on its own, length() would print one
        # count per region with the streamed output formats.
        for output in ('json', 'yaml', 'yaml-stream', 'text'):
            self.parsed_responses = [
                vpc_response('vpc-1'),
                vpc_response('vpc-2'),
            ]
            stdout, _, _ = self.run_cmd(
                [
                    'ec2',
                    'describe-vpcs',
                    '--multi-regions',
                    'us-east-1,eu-west-1',
                    '--output',
                    output,
                    '--query',
                    'length(Vpcs)',
                ]
            )
            self.assertIn('2', stdout, output)
            self.assertNotIn('1', stdout, output)

    def test_query_on_empty_responses(self):
        # Services often omit an empty list, and a query still prints its
        # result (null here) rather than nothing.
        self.parsed_responses = [{}]
        single, _, _ = self.run_cmd(
            'ec2 describe-vpcs --region us-east-1 --query Vpcs'
        )
        self.parsed_responses = [{}, {}]
        merged, _, _ = self.run_cmd(
            'ec2 describe-vpcs --multi-regions us-east-1,eu-west-1 '
            '--query Vpcs'
        )
        self.assertEqual(single, 'null\n')
        self.assertEqual(merged, single)

    def test_query_reads_the_region_from_the_top_level_object(self):
        # Only top-level objects are labelled, so a nested object's region
        # comes from its parent.
        self.parsed_responses = [
            {'Reservations': [{'Instances': [{'InstanceId': 'i-1'}]}]},
            {'Reservations': [{'Instances': [{'InstanceId': 'i-2'}]}]},
        ]
        stdout, _, _ = self.run_cmd(
            [
                'ec2',
                'describe-instances',
                '--multi-regions',
                'us-east-1,eu-west-1',
                '--query',
                'Reservations[].[_CliScope.Region, Instances[0].InstanceId]',
            ]
        )
        self.assertEqual(
            json.loads(stdout), [['us-east-1', 'i-1'], ['eu-west-1', 'i-2']]
        )


class TestLabelledObjects(BaseMultiRegionTest):
    def test_only_top_level_objects_are_labelled(self):
        self.parsed_responses = [
            {
                'Reservations': [
                    {
                        'ReservationId': 'r-1',
                        'Instances': [
                            {'InstanceId': 'i-1'},
                            {'InstanceId': 'i-2'},
                        ],
                    }
                ]
            },
            {
                'Reservations': [
                    {
                        'ReservationId': 'r-2',
                        'Instances': [{'InstanceId': 'i-3'}],
                    }
                ]
            },
        ]
        stdout, _, _ = self.run_cmd(
            'ec2 describe-instances --multi-regions us-east-1,eu-west-1'
        )
        reservations = json.loads(stdout)['Reservations']
        self.assertEqual(
            [
                (
                    reservation['ReservationId'],
                    reservation['_CliScope']['Region'],
                )
                for reservation in reservations
            ],
            [('r-1', 'us-east-1'), ('r-2', 'eu-west-1')],
        )
        self.assertEqual(
            [
                instance
                for reservation in reservations
                for instance in reservation['Instances']
            ],
            [
                {'InstanceId': 'i-1'},
                {'InstanceId': 'i-2'},
                {'InstanceId': 'i-3'},
            ],
        )

    def test_a_command_returning_a_list_of_names_is_not_supported(self):
        # The names could not say which region they came from.
        _, stderr, _ = self.run_cmd(
            'ses list-identities --multi-regions us-east-1,eu-west-1',
            expected_rc=PARAM_VALIDATION_ERROR_RC,
        )
        self.assertIn('Unknown options: --multi-regions', stderr)

    def test_a_map_is_left_alone(self):
        # Adding a key to a map would fabricate an entry the service
        # never returned.
        environment = {'Variables': {'LOG_LEVEL': 'debug'}}
        self.parsed_responses = [
            {
                'Functions': [
                    {'FunctionName': 'one', 'Environment': environment}
                ]
            },
            {'Functions': []},
        ]
        stdout, _, _ = self.run_cmd(
            'lambda list-functions --multi-regions us-east-1,eu-west-1'
        )
        function = json.loads(stdout)['Functions'][0]
        self.assertEqual(function['Environment'], environment)
        self.assertEqual(function['_CliScope'], {'Region': 'us-east-1'})
