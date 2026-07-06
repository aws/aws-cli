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
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request

from awscli.botocore.httpsession import get_cert_path
from awscli.customizations.exceptions import ConfigurationError

LOG = logging.getLogger(__name__)

_AWS_OWNED_SUFFIXES = (
    '.app.aws',
    '.portal.amazonaws.com',
    '.portal.amazonaws.com.cn',
    '.app.amazonwebservices.com.cn',
    '.portal.amazonaws.eu',
    '.api.amazonwebservices.eu',
    '.awsapps.com',
    '.awsapps.cn',
)

_AWS_OWNED_EXACT = (
    'identitycenter.amazonaws.com',
    'identitycenter.amazonaws.com.cn',
)

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
    # {idcInstanceId}.{region}.portal.amazonaws.com.cn
    re.compile(
        r'^[^.]+\.(?P<region>[a-z0-9-]+)\.portal\.amazonaws\.com\.cn$',
        re.IGNORECASE,
    ),
    # {idcInstanceId}.portal.{region}.app.amazonwebservices.com.cn
    re.compile(
        r'^[^.]+\.portal\.(?P<region>[a-z0-9-]+)\.app\.amazonwebservices\.com\.cn$',
        re.IGNORECASE,
    ),
    # {idcInstanceId}.{region}.portal.amazonaws.eu
    re.compile(
        r'^[^.]+\.(?P<region>[a-z0-9-]+)\.portal\.amazonaws\.eu$',
        re.IGNORECASE,
    ),
    # {idcInstanceId}.portal.{region}.api.amazonwebservices.eu
    re.compile(
        r'^[^.]+\.portal\.(?P<region>[a-z0-9-]+)\.api\.amazonwebservices\.eu$',
        re.IGNORECASE,
    ),
)

_MAX_REDIRECTS = 1

_DEFAULT_PORTS = {'https': 443, 'http': 80}

_DEFAULT_TIMEOUT = 10


def _normalize_url(url):
    parsed = urllib.parse.urlparse(url)
    netloc = parsed.hostname or ''
    if parsed.port and parsed.port != _DEFAULT_PORTS.get(parsed.scheme):
        netloc = f'{netloc}:{parsed.port}'
    path = parsed.path.rstrip('/')
    return urllib.parse.urlunparse((parsed.scheme, netloc, path, '', '', ''))


def is_aws_owned_domain(hostname):
    hostname = hostname.lower().rstrip('.')
    if hostname in _AWS_OWNED_EXACT:
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


def _follow_redirect(url, timeout=_DEFAULT_TIMEOUT, verify=None):
    class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    ssl_context = ssl.create_default_context()
    if verify is False:
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
    elif verify and verify is not True:
        if os.path.isdir(verify):
            ssl_context.load_verify_locations(capath=verify)
        else:
            ssl_context.load_verify_locations(cafile=verify)
    else:
        ssl_context.load_verify_locations(cafile=get_cert_path(True))
    https_handler = urllib.request.HTTPSHandler(context=ssl_context)
    opener = urllib.request.build_opener(_NoRedirectHandler, https_handler)
    redirect_codes = (301, 302, 303, 307, 308)

    for _ in range(_MAX_REDIRECTS):
        try:
            LOG.debug("Issuing HEAD request to '%s'", url)
            req = urllib.request.Request(url, method='HEAD')
            resp = opener.open(req, timeout=timeout)
            resp.close()
            LOG.debug(
                "HEAD request to '%s' returned %s (no redirect)",
                url,
                resp.status,
            )
            return url
        except urllib.error.HTTPError as e:
            if e.code in (405, 501):
                LOG.debug(
                    "HEAD request returned %s, falling back to GET", e.code
                )
                try:
                    req = urllib.request.Request(url, method='GET')
                    resp = opener.open(req, timeout=timeout)
                    resp.close()
                    LOG.debug(
                        "GET request to '%s' returned %s (no redirect)",
                        url,
                        resp.status,
                    )
                    return url
                except urllib.error.HTTPError as e2:
                    if e2.code in redirect_codes:
                        location = e2.headers.get('Location')
                        if not location:
                            raise ConfigurationError(
                                "Redirect response missing Location header."
                            )
                        LOG.debug(
                            "GET request returned %s, redirecting to '%s'",
                            e2.code,
                            location,
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
                LOG.debug(
                    "HEAD request returned %s, redirecting to '%s'",
                    e.code,
                    location,
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


def resolve_start_url(
    start_url,
    session,
    configured_region=None,
    timeout=None,
    verify=None,
):
    parsed = urllib.parse.urlparse(start_url)

    if parsed.scheme != 'https':
        raise ConfigurationError(
            "The sso_start_url must use the https scheme."
        )

    hostname = parsed.hostname
    if not hostname:
        raise ConfigurationError(f"Invalid sso_start_url: '{start_url}'")

    if is_aws_owned_domain(hostname):
        if not configured_region:
            raise ConfigurationError(
                "Missing required configuration: sso_region. "
                "Please run 'aws configure sso' to set it."
            )
        return start_url, configured_region

    LOG.debug(
        "Start URL '%s' is not AWS-owned, following redirects", start_url
    )
    effective_timeout = timeout if timeout is not None else _DEFAULT_TIMEOUT
    resolved_url = _normalize_url(
        _follow_redirect(
            start_url,
            timeout=effective_timeout,
            verify=verify,
        )
    )

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

    region = _extract_region_from_hostname(resolved_hostname)

    if not region:
        if configured_region:
            region = configured_region
        else:
            raise ConfigurationError(
                f"Cannot determine region from start URL '{start_url}'. "
                f"Please provide sso_region in your configuration."
            )

    return resolved_url, region
