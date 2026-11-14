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
import socket
from unittest import mock

import pytest
from botocore.exceptions import (
    ClientError,
    ConnectTimeoutError,
    EndpointConnectionError,
    NoCredentialsError,
    PartialCredentialsError,
    SSLError,
)
from urllib3.exceptions import NewConnectionError

from awscli.customizations.exceptions import ConfigurationError
from awscli.customizations.multiregion.caller import _is_dns_failure
from awscli.customizations.multiregion.resolution import resolve_regions
from awscli.customizations.multiregion.validation import MultiRegionSpec

ENABLED_STATUSES = ['ENABLED', 'ENABLED_BY_DEFAULT']


def account_client(regions=None, error=None):
    """A mock ``account`` client that answers ``list_regions``."""
    client = mock.Mock()
    page = {'Regions': [{'RegionName': name} for name in regions or []]}
    paginate = client.get_paginator.return_value.paginate
    if error is not None:
        client.list_regions.side_effect = error
        paginate.side_effect = error
    else:
        client.list_regions.return_value = page
        paginate.return_value = [page]
    return client


def ec2_client(regions=None, error=None):
    """A mock ``ec2`` client that answers ``describe_regions``.

    ``regions`` is a list of ``(region_name, opt_in_status)`` pairs.
    """
    client = mock.Mock()
    if error is not None:
        client.describe_regions.side_effect = error
    else:
        client.describe_regions.return_value = {
            'Regions': [
                {'RegionName': name, 'OptInStatus': status}
                for name, status in regions or []
            ]
        }
    return client


def make_session(
    region='us-east-1', partition='aws', clients=None, config=None
):
    """A session mock with no endpoint data for any service."""
    session = mock.Mock()
    config = dict(config or {}, region=region)
    session.get_config_variable.side_effect = config.get
    resolver = mock.Mock()
    resolver.get_partition_for_region.return_value = partition
    session._get_internal_component.return_value = resolver
    session.get_available_regions.return_value = []
    available_clients = clients or {}

    def create_client(service_name, **kwargs):
        if service_name not in available_clients:
            raise AssertionError(f'unexpected client created: {service_name}')
        return available_clients[service_name]

    session.create_client.side_effect = create_client
    return session


def all_regions_spec():
    return MultiRegionSpec()


class TestResolveExplicitRegions:
    def test_returns_listed_regions_unchanged(self):
        session = make_session()
        spec = MultiRegionSpec(
            regions=['us-west-2', 'eu-west-1'],
        )

        resolved = resolve_regions(session, spec, 'ec2')

        assert resolved.regions == ['us-west-2', 'eu-west-1']
        assert resolved.skip_missing_hosts is False

    def test_keeps_region_where_service_has_no_endpoint(self):
        # The service only exists in us-east-1, but the user asked for
        # eu-west-1 too and must hear about it.
        session = make_session()
        session.get_available_regions.return_value = ['us-east-1']
        spec = MultiRegionSpec(
            regions=['us-east-1', 'eu-west-1'],
        )

        resolved = resolve_regions(session, spec, 'cloudfront')

        assert resolved.regions == ['us-east-1', 'eu-west-1']
        assert resolved.skip_missing_hosts is False

    def test_does_not_call_any_region_lister(self):
        session = make_session()
        spec = MultiRegionSpec(['us-east-1'])

        resolve_regions(session, spec, 'ec2')

        assert session.create_client.call_args_list == []


class TestResolveAllRegions:
    def test_intersects_enabled_and_service_regions(self):
        session = make_session(
            clients={
                'account': account_client(
                    ['us-east-1', 'eu-west-1', 'ap-south-1']
                )
            }
        )
        session.get_available_regions.return_value = [
            'us-east-1',
            'eu-west-1',
            'us-west-2',
        ]

        resolved = resolve_regions(session, all_regions_spec(), 'ec2')

        assert resolved.regions == ['eu-west-1', 'us-east-1']
        assert resolved.skip_missing_hosts is False

    def test_sorts_regions_alphabetically(self):
        enabled = ['us-west-2', 'ap-south-1', 'eu-west-1', 'us-east-1']
        session = make_session(clients={'account': account_client(enabled)})
        session.get_available_regions.return_value = list(enabled)

        resolved = resolve_regions(session, all_regions_spec(), 'ec2')

        assert resolved.regions == [
            'ap-south-1',
            'eu-west-1',
            'us-east-1',
            'us-west-2',
        ]

    def test_looks_up_service_regions_in_current_partition(self):
        session = make_session(
            region='cn-north-1',
            partition='aws-cn',
            clients={'account': account_client(['cn-north-1'])},
        )
        session.get_available_regions.return_value = ['cn-north-1']

        resolved = resolve_regions(session, all_regions_spec(), 'ec2')

        session.get_available_regions.assert_called_once_with('ec2', 'aws-cn')
        assert resolved.regions == ['cn-north-1']

    @pytest.mark.parametrize(
        'setting', ['use_fips_endpoint', 'use_dualstack_endpoint']
    )
    def test_lets_dns_decide_with_an_endpoint_variant(self, setting):
        # The endpoint data does not list every FIPS or dual-stack
        # endpoint that exists, so every region with the service is
        # called and a missing hostname leaves the region out.
        session = make_session(
            clients={'account': account_client(['us-east-1', 'eu-west-1'])},
            config={setting: 'true'},
        )
        session.get_available_regions.return_value = ['us-east-1', 'eu-west-1']

        resolved = resolve_regions(session, all_regions_spec(), 'ec2')

        assert resolved.regions == ['eu-west-1', 'us-east-1']
        assert resolved.skip_missing_hosts is True

    def test_calls_every_enabled_region_without_endpoint_data(self):
        # A service missing from endpoints.json has no region list, so
        # every enabled region is called and DNS decides.
        session = make_session(
            clients={'account': account_client(['us-west-2', 'us-east-1'])}
        )
        session.get_available_regions.return_value = []

        resolved = resolve_regions(session, all_regions_spec(), 'newservice')

        assert resolved.regions == ['us-east-1', 'us-west-2']
        assert resolved.skip_missing_hosts is True

    def test_raises_when_service_in_no_enabled_region(self):
        session = make_session(
            clients={'account': account_client(['ap-south-1'])}
        )
        session.get_available_regions.return_value = ['us-east-1']

        with pytest.raises(ConfigurationError) as excinfo:
            resolve_regions(session, all_regions_spec(), 's3')

        assert 's3' in str(excinfo.value)

    def test_explains_how_to_set_a_region_without_one(self):
        # --region cannot be used with --multi-regions, so the usual
        # "You must specify a region" advice does not apply.
        session = make_session(region=None)

        with pytest.raises(ConfigurationError) as excinfo:
            resolve_regions(session, all_regions_spec(), 'ec2')

        assert 'AWS_REGION' in str(excinfo.value)

        assert session.create_client.call_args_list == []


class TestListEnabledRegions:
    def test_prefers_account_list_regions(self):
        account = account_client(['us-east-1'])
        session = make_session(clients={'account': account})
        session.get_available_regions.return_value = ['us-east-1']

        resolved = resolve_regions(session, all_regions_spec(), 'ec2')

        assert resolved.regions == ['us-east-1']
        session.create_client.assert_called_once_with(
            'account', region_name='us-east-1', verify=None
        )

    def test_requests_only_enabled_opt_statuses_when_paginating(self):
        account = account_client(['us-east-1'])
        session = make_session(clients={'account': account})
        session.get_available_regions.return_value = ['us-east-1']

        resolve_regions(session, all_regions_spec(), 'ec2')

        account.get_paginator.assert_called_once_with('list_regions')
        account.get_paginator.return_value.paginate.assert_called_once_with(
            RegionOptStatusContains=ENABLED_STATUSES
        )

    def test_collects_regions_from_every_page(self):
        account = account_client()
        account.get_paginator.return_value.paginate.return_value = [
            {'Regions': [{'RegionName': 'us-east-1'}]},
            {'Regions': [{'RegionName': 'eu-west-1'}]},
        ]
        session = make_session(clients={'account': account})
        session.get_available_regions.return_value = [
            'us-east-1',
            'eu-west-1',
        ]

        resolved = resolve_regions(session, all_regions_spec(), 'ec2')

        assert resolved.regions == ['eu-west-1', 'us-east-1']

    def test_falls_back_to_ec2_describe_regions(self):
        account = account_client(error=access_denied('ListRegions'))
        ec2 = ec2_client(
            [
                ('us-east-1', 'opt-in-not-required'),
                ('eu-west-1', 'opted-in'),
            ]
        )
        session = make_session(clients={'account': account, 'ec2': ec2})
        session.get_available_regions.return_value = [
            'us-east-1',
            'eu-west-1',
        ]

        resolved = resolve_regions(session, all_regions_spec(), 'ec2')

        assert resolved.regions == ['eu-west-1', 'us-east-1']
        assert session.create_client.call_args_list == [
            mock.call('account', region_name='us-east-1', verify=None),
            mock.call('ec2', region_name='us-east-1', verify=None),
        ]
        ec2.describe_regions.assert_called_once_with()

    def test_raises_with_both_errors_when_both_listers_fail(self):
        account = account_client(error=access_denied('ListRegions'))
        ec2 = ec2_client(error=ConnectTimeoutError(endpoint_url='https://x'))
        session = make_session(clients={'account': account, 'ec2': ec2})

        with pytest.raises(ConfigurationError) as excinfo:
            resolve_regions(session, all_regions_spec(), 'ec2')

        message = str(excinfo.value)
        assert 'not authorized to perform: account:ListRegions' in message
        assert 'Connect timeout' in message
        assert '--multi-regions' in message

    @pytest.mark.parametrize(
        'error',
        [
            NoCredentialsError(),
            PartialCredentialsError(provider='env', cred_var='key'),
            ClientError(
                {'Error': {'Code': 'ExpiredTokenException', 'Message': 'x'}},
                'ListRegions',
            ),
            ClientError(
                {'Error': {'Code': 'UnrecognizedClientException'}},
                'ListRegions',
            ),
        ],
    )
    def test_credential_errors_are_raised_as_they_are(self, error):
        # Every region would fail the same way, so the user is not told to
        # list the regions explicitly, and ec2 is not tried.
        account = account_client(error=error)
        session = make_session(clients={'account': account})

        with pytest.raises(type(error)) as excinfo:
            resolve_regions(session, all_regions_spec(), 'ec2')

        assert excinfo.value is error
        assert session.create_client.call_count == 1

    def test_does_not_swallow_unexpected_errors(self):
        account = account_client(error=ValueError('boom'))
        session = make_session(clients={'account': account})

        with pytest.raises(ValueError):
            resolve_regions(session, all_regions_spec(), 'ec2')


def access_denied(operation_name):
    return ClientError(
        {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': (
                    'User is not authorized to perform: '
                    f'account:{operation_name}'
                ),
            }
        },
        operation_name,
    )


def connection_error(resolver_error, chained='cause'):
    """The exception botocore raises when a connection cannot be made.

    urllib3 2.x raises its own error ``from`` the resolver error, so it is
    the ``__cause__``; urllib3 1.x raises it while handling the resolver
    error, so it is only the ``__context__``.  botocore then re-raises it
    as ``EndpointConnectionError(endpoint_url=..., error=e)``.
    """
    try:
        try:
            raise resolver_error
        except OSError as e:
            if chained == 'cause':
                raise NewConnectionError(None, 'Failed to connect') from e
            raise NewConnectionError(None, 'Failed to connect')
    except NewConnectionError as wrapped:
        return EndpointConnectionError(
            endpoint_url='https://newservice.ap-east-1.amazonaws.com',
            error=wrapped,
        )


NO_SUCH_HOST_ERRNOS = [socket.EAI_NONAME] + (
    [socket.EAI_NODATA] if hasattr(socket, 'EAI_NODATA') else []
)


class TestIsDnsFailure:
    @pytest.mark.parametrize('errno', NO_SUCH_HOST_ERRNOS)
    @pytest.mark.parametrize('chained', ['cause', 'context'])
    def test_missing_hostname_is_dns_failure(self, errno, chained):
        error = connection_error(socket.gaierror(errno, 'not known'), chained)
        assert _is_dns_failure(error) is True

    def test_temporary_dns_failure_is_not_missing_hostname(self):
        # The hostname may exist; the failure is reported rather than the
        # region being quietly dropped from the output.
        error = connection_error(socket.gaierror(socket.EAI_AGAIN, 'again'))
        assert _is_dns_failure(error) is False

    def test_connection_refused_is_not_dns_failure(self):
        error = connection_error(ConnectionRefusedError(61, 'refused'))
        assert _is_dns_failure(error) is False

    @pytest.mark.parametrize(
        'exception_factory',
        [
            lambda: access_denied('DescribeVpcs'),
            # The right wrapped error, but a timeout is not a DNS answer.
            lambda: ConnectTimeoutError(
                endpoint_url='https://newservice.ap-east-1.amazonaws.com',
                error=socket.gaierror(socket.EAI_NONAME, 'not known'),
            ),
            lambda: SSLError(
                endpoint_url='https://newservice.ap-east-1.amazonaws.com',
                error='certificate verify failed',
            ),
            lambda: ValueError('boom'),
            # An EndpointConnectionError raised without a wrapped error.
            lambda: EndpointConnectionError(
                endpoint_url='https://newservice.ap-east-1.amazonaws.com'
            ),
        ],
    )
    def test_other_errors_are_not_dns_failures(self, exception_factory):
        assert _is_dns_failure(exception_factory()) is False


class TestRegionDiscoveryHonoursGlobalArgs:
    """The discovery calls are API calls and must behave like one."""

    def test_verify_is_passed_to_the_account_client(self):
        account = account_client(['us-east-1'])
        session = make_session(clients={'account': account})
        session.get_available_regions.return_value = ['us-east-1']

        resolve_regions(session, all_regions_spec(), 'ec2', verify=False)

        session.create_client.assert_called_once_with(
            'account', region_name='us-east-1', verify=False
        )

    def test_verify_is_passed_to_the_ec2_fallback_client(self):
        account = account_client(error=access_denied('ListRegions'))
        ec2 = ec2_client([('us-east-1', 'opt-in-not-required')])
        session = make_session(clients={'account': account, 'ec2': ec2})
        session.get_available_regions.return_value = ['us-east-1']

        resolve_regions(
            session, all_regions_spec(), 'ec2', verify='/tmp/bundle.pem'
        )

        assert session.create_client.call_args_list == [
            mock.call(
                'account', region_name='us-east-1', verify='/tmp/bundle.pem'
            ),
            mock.call(
                'ec2', region_name='us-east-1', verify='/tmp/bundle.pem'
            ),
        ]


class TestEmptyEnabledRegionList:
    """An account always has at least one enabled region.

    An empty answer therefore means the source could not tell us, not
    that the account has no regions.
    """

    def test_empty_account_answer_falls_through_to_ec2(self):
        account = account_client([])
        ec2 = ec2_client([('eu-west-1', 'opted-in')])
        session = make_session(clients={'account': account, 'ec2': ec2})
        session.get_available_regions.return_value = ['eu-west-1']

        resolved = resolve_regions(session, all_regions_spec(), 'ec2')

        assert resolved.regions == ['eu-west-1']

    def test_both_sources_empty_is_a_configuration_error(self):
        account = account_client([])
        ec2 = ec2_client([])
        session = make_session(clients={'account': account, 'ec2': ec2})

        with pytest.raises(ConfigurationError) as excinfo:
            resolve_regions(session, all_regions_spec(), 'ec2')

        assert 'could not determine which regions are enabled' in str(
            excinfo.value
        )

    def test_error_names_both_sources_that_came_back_empty(self):
        account = account_client([])
        ec2 = ec2_client([])
        session = make_session(clients={'account': account, 'ec2': ec2})

        with pytest.raises(ConfigurationError) as excinfo:
            resolve_regions(session, all_regions_spec(), 'ec2')

        message = str(excinfo.value)
        assert message.count('returned no regions') == 2
        assert '--multi-regions <region>,<region>' in message
