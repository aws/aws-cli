# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import urllib.error

import pytest

from awscli.customizations.exceptions import ConfigurationError
from awscli.customizations.sso.resolve import (
    _extract_region_from_hostname,
    _follow_redirect,
    is_aws_owned_domain,
    resolve_start_url,
)
from awscli.testutils import mock


class TestIsAwsOwnedDomain:
    @pytest.mark.parametrize(
        'hostname',
        [
            'ssoins-abc123.portal.us-west-2.app.aws',
            'ssoins-abc123.portal.us-east-1.app.aws',
            'SSOINS-ABC123.PORTAL.US-WEST-2.APP.AWS',
            'ssoins-abc123.us-west-2.portal.amazonaws.com',
            'd-abc123.awsapps.com',
            'myalias.awsapps.com',
            'awsapps.com',
            'identitycenter.amazonaws.com',
            'identitycenter.amazonaws.com.',
        ],
    )
    def test_aws_owned_returns_true(self, hostname):
        assert is_aws_owned_domain(hostname) is True

    @pytest.mark.parametrize(
        'hostname',
        [
            'aws.mycompany.com',
            'awsapps.com.evil.net',
            'evil-awsapps.com',
            'x.app.aws.example.com',
            'amazonaws.com.example.net',
            'portal.amazonaws.com.evil.net',
            'notidentitycenter.amazonaws.com',
            'example.com',
            '',
        ],
    )
    def test_non_aws_owned_returns_false(self, hostname):
        assert is_aws_owned_domain(hostname) is False


class TestExtractRegionFromHostname:
    @pytest.mark.parametrize(
        'hostname, expected_region',
        [
            ('ssoins-abc.portal.us-west-2.app.aws', 'us-west-2'),
            ('ssoins-abc.portal.us-east-1.app.aws', 'us-east-1'),
            ('ssoins-abc.portal.eu-west-1.app.aws', 'eu-west-1'),
            ('ssoins-abc.portal.cn-north-1.app.aws', 'cn-north-1'),
            ('ssoins-abc.us-gov-west-1.portal.amazonaws.com', 'us-gov-west-1'),
            ('ssoins-abc.us-west-2.portal.amazonaws.com', 'us-west-2'),
        ],
    )
    def test_extracts_region(self, hostname, expected_region):
        assert _extract_region_from_hostname(hostname) == expected_region

    @pytest.mark.parametrize(
        'hostname',
        [
            'd-abc123.awsapps.com',
            'identitycenter.amazonaws.com',
            'aws.mycompany.com',
        ],
    )
    def test_returns_none_for_region_less_hostnames(self, hostname):
        assert _extract_region_from_hostname(hostname) is None


class TestResolveStartUrl:
    def _mock_session(self, regions=None):
        if regions is None:
            regions = [
                'us-east-1',
                'us-west-2',
                'eu-west-1',
                'us-gov-west-1',
                'cn-north-1',
            ]
        session = mock.Mock()
        session.get_available_regions.return_value = regions
        return session

    def test_aws_owned_url_returns_configured_region(self):
        session = self._mock_session()
        resolved_url, region = resolve_start_url(
            'https://ssoins-abc.portal.us-west-2.app.aws',
            session=session,
            configured_region='us-west-2',
        )
        assert resolved_url == 'https://ssoins-abc.portal.us-west-2.app.aws'
        assert region == 'us-west-2'

    def test_aws_owned_url_no_network_call(self):
        session = self._mock_session()
        with mock.patch('urllib.request.build_opener') as mock_opener:
            resolve_start_url(
                'https://ssoins-abc.portal.us-west-2.app.aws',
                session=session,
                configured_region='us-west-2',
            )
            mock_opener.assert_not_called()

    def test_aws_owned_url_without_configured_region_raises_error(self):
        session = self._mock_session()
        with pytest.raises(
            ConfigurationError,
            match='Missing required configuration: sso_region',
        ):
            resolve_start_url(
                'https://ssoins-abc.portal.us-west-2.app.aws',
                session=session,
            )

    def test_aws_owned_url_uses_configured_region_not_hostname(self):
        session = self._mock_session()
        resolved_url, region = resolve_start_url(
            'https://ssoins-abc.portal.us-west-2.app.aws',
            session=session,
            configured_region='us-east-1',
        )
        assert region == 'us-east-1'

    def test_awsapps_url_requires_configured_region(self):
        session = self._mock_session()
        with pytest.raises(
            ConfigurationError,
            match='Missing required configuration: sso_region',
        ):
            resolve_start_url(
                'https://d-abc123.awsapps.com/start',
                session=session,
            )

    def test_awsapps_url_uses_configured_region(self):
        session = self._mock_session()
        resolved_url, region = resolve_start_url(
            'https://d-abc123.awsapps.com/start',
            session=session,
            configured_region='us-east-1',
        )
        assert resolved_url == 'https://d-abc123.awsapps.com/start'
        assert region == 'us-east-1'

    def test_http_scheme_raises_error(self):
        session = self._mock_session()
        with pytest.raises(ConfigurationError, match='https scheme'):
            resolve_start_url('http://aws.mycompany.com', session=session)

    def test_invalid_url_raises_error(self):
        session = self._mock_session()
        with pytest.raises(ConfigurationError, match='Invalid sso_start_url'):
            resolve_start_url('https://', session=session)

    def test_vanity_url_invalid_region_raises_error(self):
        session = self._mock_session(regions=['us-east-1', 'us-west-2'])
        with mock.patch(
            'awscli.customizations.sso.resolve._follow_redirect'
        ) as mock_follow:
            mock_follow.return_value = (
                'https://ssoins-abc.portal.fake-region-1.app.aws'
            )
            with pytest.raises(
                ConfigurationError, match='not a known AWS region'
            ):
                resolve_start_url(
                    'https://aws.mycompany.com',
                    session=session,
                )

    def test_vanity_url_invalid_region_does_not_fall_back_to_configured(self):
        session = self._mock_session(regions=['us-east-1', 'us-west-2'])
        with mock.patch(
            'awscli.customizations.sso.resolve._follow_redirect'
        ) as mock_follow:
            mock_follow.return_value = (
                'https://ssoins-abc.portal.fake-region-1.app.aws'
            )
            with pytest.raises(
                ConfigurationError, match='not a known AWS region'
            ):
                resolve_start_url(
                    'https://aws.mycompany.com',
                    session=session,
                    configured_region='us-east-1',
                )

    def test_vanity_url_govcloud_region_accepted(self):
        session = mock.Mock()
        session.get_available_regions.side_effect = (
            lambda service, partition_name='aws': {
                'aws': ['us-east-1', 'us-west-2'],
                'aws-us-gov': ['us-gov-west-1'],
                'aws-cn': ['cn-north-1'],
            }.get(partition_name, [])
        )
        with mock.patch(
            'awscli.customizations.sso.resolve._follow_redirect'
        ) as mock_follow:
            mock_follow.return_value = (
                'https://ssoins-abc.portal.us-gov-west-1.app.aws'
            )
            resolved_url, region = resolve_start_url(
                'https://aws.mycompany.com',
                session=session,
            )
            assert region == 'us-gov-west-1'

    def test_vanity_url_china_region_accepted(self):
        session = mock.Mock()
        session.get_available_regions.side_effect = (
            lambda service, partition_name='aws': {
                'aws': ['us-east-1', 'us-west-2'],
                'aws-us-gov': ['us-gov-west-1'],
                'aws-cn': ['cn-north-1'],
            }.get(partition_name, [])
        )
        with mock.patch(
            'awscli.customizations.sso.resolve._follow_redirect'
        ) as mock_follow:
            mock_follow.return_value = (
                'https://ssoins-abc.portal.cn-north-1.app.aws'
            )
            resolved_url, region = resolve_start_url(
                'https://aws.mycompany.com',
                session=session,
            )
            assert region == 'cn-north-1'

    def test_vanity_url_follows_redirect(self):
        session = self._mock_session()
        redirect_url = 'https://ssoins-abc.portal.us-east-1.app.aws:443/'

        with mock.patch(
            'awscli.customizations.sso.resolve._follow_redirect'
        ) as mock_follow:
            mock_follow.return_value = redirect_url
            resolved_url, region = resolve_start_url(
                'https://aws.mycompany.com',
                session=session,
            )
            assert resolved_url == redirect_url
            assert region == 'us-east-1'
            mock_follow.assert_called_once_with('https://aws.mycompany.com')

    def test_vanity_url_resolves_to_non_aws_domain_raises_error(self):
        session = self._mock_session()
        with mock.patch(
            'awscli.customizations.sso.resolve._follow_redirect'
        ) as mock_follow:
            mock_follow.return_value = 'https://not-aws.example.com'
            with pytest.raises(ConfigurationError, match='Could not resolve'):
                resolve_start_url('https://aws.mycompany.com', session=session)

    def test_vanity_url_resolves_to_http_raises_error(self):
        session = self._mock_session()
        with mock.patch(
            'awscli.customizations.sso.resolve._follow_redirect'
        ) as mock_follow:
            mock_follow.return_value = (
                'http://ssoins-abc.portal.us-east-1.app.aws'
            )
            with pytest.raises(ConfigurationError, match='must use https'):
                resolve_start_url('https://aws.mycompany.com', session=session)


class TestFollowRedirect:
    def _make_http_error(self, code, headers=None):
        if headers is None:
            headers = {}
        import http.client

        msg = http.client.HTTPMessage()
        for k, v in headers.items():
            msg[k] = v
        return urllib.error.HTTPError(
            url='https://example.com',
            code=code,
            msg='',
            hdrs=msg,
            fp=None,
        )

    def test_head_redirect_returns_location(self):
        redirect_target = 'https://ssoins-abc.portal.us-east-1.app.aws'
        with mock.patch('urllib.request.build_opener') as mock_build:
            mock_opener = mock.Mock()
            mock_build.return_value = mock_opener
            mock_opener.open.side_effect = self._make_http_error(
                302, {'Location': redirect_target}
            )
            result = _follow_redirect('https://aws.mycompany.com')
            assert result == redirect_target

    @pytest.mark.parametrize('head_error_code', [405, 501])
    def test_head_unsupported_falls_back_to_get(self, head_error_code):
        redirect_target = 'https://ssoins-abc.portal.us-east-1.app.aws'
        with mock.patch('urllib.request.build_opener') as mock_build:
            mock_opener = mock.Mock()
            mock_build.return_value = mock_opener
            mock_opener.open.side_effect = [
                self._make_http_error(head_error_code),
                self._make_http_error(302, {'Location': redirect_target}),
            ]
            result = _follow_redirect('https://aws.mycompany.com')
            assert result == redirect_target
            assert mock_opener.open.call_count == 2

    def test_head_200_returns_original_url(self):
        with mock.patch('urllib.request.build_opener') as mock_build:
            mock_opener = mock.Mock()
            mock_build.return_value = mock_opener
            mock_response = mock.Mock()
            mock_opener.open.return_value = mock_response
            result = _follow_redirect('https://aws.mycompany.com')
            assert result == 'https://aws.mycompany.com'
            mock_response.close.assert_called_once()

    def test_missing_location_header_raises_error(self):
        with mock.patch('urllib.request.build_opener') as mock_build:
            mock_opener = mock.Mock()
            mock_build.return_value = mock_opener
            mock_opener.open.side_effect = self._make_http_error(302, {})
            with pytest.raises(ConfigurationError, match='missing Location'):
                _follow_redirect('https://aws.mycompany.com')

    def test_non_redirect_error_raises_configuration_error(self):
        with mock.patch('urllib.request.build_opener') as mock_build:
            mock_opener = mock.Mock()
            mock_build.return_value = mock_opener
            mock_opener.open.side_effect = self._make_http_error(500)
            with pytest.raises(ConfigurationError, match='HTTP 500'):
                _follow_redirect('https://aws.mycompany.com')

    def test_url_error_raises_configuration_error(self):
        with mock.patch('urllib.request.build_opener') as mock_build:
            mock_opener = mock.Mock()
            mock_build.return_value = mock_opener
            mock_opener.open.side_effect = urllib.error.URLError(
                'Name or service not known'
            )
            with pytest.raises(ConfigurationError, match='Name or service'):
                _follow_redirect('https://aws.mycompany.com')

    def test_relative_location_is_resolved(self):
        with mock.patch('urllib.request.build_opener') as mock_build:
            mock_opener = mock.Mock()
            mock_build.return_value = mock_opener
            mock_opener.open.side_effect = self._make_http_error(
                302, {'Location': '/start'}
            )
            result = _follow_redirect('https://aws.mycompany.com/portal')
            assert result == 'https://aws.mycompany.com/start'

    def test_stops_after_max_redirects(self):
        intermediate = 'https://intermediate.example.com/path'
        with mock.patch('urllib.request.build_opener') as mock_build:
            mock_opener = mock.Mock()
            mock_build.return_value = mock_opener
            mock_opener.open.side_effect = self._make_http_error(
                302, {'Location': intermediate}
            )
            result = _follow_redirect('https://aws.mycompany.com')
            assert result == intermediate
            assert mock_opener.open.call_count == 1
