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
import logging
import re
import urllib.error
import urllib.parse
import urllib.request

from awscli.customizations.exceptions import ConfigurationError

LOG = logging.getLogger(__name__)

_AWS_OWNED_SUFFIXES = (
    '.app.aws',
    '.portal.amazonaws.com',
    '.awsapps.com',
)

_AWS_OWNED_EXACT = 'identitycenter.amazonaws.com'

_REGION_PATTERNS = (
    # {idcInstanceId}.portal.{region}.app.aws
    re.compile(
        r'^[^.]+\.portal\.(?P<region>[a-z0-9-]+)\.app\.aws$', re.IGNORECASE
    ),
    # {idcInstanceId}.{region}.portal.amazonaws.com
    re.compile(
        r'^[^.]+\.(?P<region>[a-z0-9-]+)\.portal\.amazonaws\.com$',
        re.IGNORECASE,
    ),
)

_ALL_PARTITIONS = ('aws', 'aws-cn', 'aws-us-gov')

_MAX_REDIRECTS = 1


def is_aws_owned_domain(hostname):
    hostname = hostname.lower().rstrip('.')
    if hostname == _AWS_OWNED_EXACT:
        return True
    for suffix in _AWS_OWNED_SUFFIXES:
        if hostname == suffix.lstrip('.'):
            return True
        if hostname.endswith(suffix):
            return True
    return False


def _extract_region_from_hostname(hostname):
    hostname = hostname.lower().rstrip('.')
    for pattern in _REGION_PATTERNS:
        match = pattern.match(hostname)
        if match:
            return match.group('region')
    return None


def _validate_region(region, session):
    available = set()
    for partition in _ALL_PARTITIONS:
        available.update(
            session.get_available_regions('sso-oidc', partition_name=partition)
        )
    if region not in available:
        raise ConfigurationError(
            f"Region '{region}' parsed from the resolved start URL is not "
            f"a known AWS region. Verify the start URL is correct."
        )


def _follow_redirect(url):
    class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(_NoRedirectHandler)
    redirect_codes = (301, 302, 303, 307, 308)

    for _attempt in range(_MAX_REDIRECTS):
        try:
            req = urllib.request.Request(url, method='HEAD')
            resp = opener.open(req, timeout=10)
            resp.close()
            return url
        except urllib.error.HTTPError as e:
            if e.code == 405:
                try:
                    req = urllib.request.Request(url, method='GET')
                    resp = opener.open(req, timeout=10)
                    resp.close()
                    return url
                except urllib.error.HTTPError as e2:
                    if e2.code in redirect_codes:
                        location = e2.headers.get('Location')
                        if not location:
                            raise ConfigurationError(
                                "Redirect response missing Location header."
                            )
                        url = urllib.parse.urljoin(url, location)
                    else:
                        raise ConfigurationError(
                            f"Failed to resolve start URL: HTTP {e2.code}"
                        )
                except urllib.error.URLError as e2:
                    raise ConfigurationError(
                        f"Failed to resolve start URL: {e2.reason}"
                    )
            elif e.code in redirect_codes:
                location = e.headers.get('Location')
                if not location:
                    raise ConfigurationError(
                        "Redirect response missing Location header."
                    )
                url = urllib.parse.urljoin(url, location)
            else:
                raise ConfigurationError(
                    f"Failed to resolve start URL: HTTP {e.code}"
                )
        except urllib.error.URLError as e:
            raise ConfigurationError(
                f"Failed to resolve start URL: {e.reason}"
            )

    return url


def resolve_start_url(start_url, session, configured_region=None):
    parsed = urllib.parse.urlparse(start_url)

    if parsed.scheme != 'https':
        raise ConfigurationError(
            "The sso_start_url must use the https scheme."
        )

    hostname = parsed.hostname
    if not hostname:
        raise ConfigurationError(f"Invalid sso_start_url: '{start_url}'")

    if is_aws_owned_domain(hostname):
        resolved_url = start_url
    else:
        LOG.debug(
            "Start URL '%s' is not AWS-owned, following redirects", start_url
        )
        resolved_url = _follow_redirect(start_url)

        resolved_hostname = urllib.parse.urlparse(resolved_url).hostname
        if not resolved_hostname or not is_aws_owned_domain(resolved_hostname):
            raise ConfigurationError(
                f"Could not resolve start URL '{start_url}' to an "
                f"AWS-owned endpoint. Final URL: '{resolved_url}'"
            )

        if urllib.parse.urlparse(resolved_url).scheme != 'https':
            raise ConfigurationError(
                f"Resolved URL must use https. Got: '{resolved_url}'"
            )

    resolved_hostname = urllib.parse.urlparse(resolved_url).hostname
    region = _extract_region_from_hostname(resolved_hostname)

    if region:
        _validate_region(region, session)
    elif configured_region:
        region = configured_region
    else:
        raise ConfigurationError(
            f"Cannot determine region from start URL '{start_url}'. "
            f"Please provide sso_region in your configuration."
        )

    return resolved_url, region
