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
import argparse
import sys

from awscli.customizations.lambdaweb import constants
from awscli.formatter import get_formatter


def console_url(partition, region, function_name):
    """Return the partition-aware AWS console URL for a Lambda Web Function."""
    if not partition or not region or not function_name:
        raise ValueError('partition, region, and function_name are required')
    domain = constants.CONSOLE_DOMAIN_BY_PARTITION.get(partition)
    if domain is None:
        return ''
    return (
        f'https://{region}.{domain}{constants.CONSOLE_HOST_PATH}'
        f'{constants.CONSOLE_WEB_FUNCTION_FRAGMENT}{function_name}'
    )


def _https_url(domain_or_url):
    if not domain_or_url:
        return ''
    if domain_or_url.startswith('https://'):
        return domain_or_url
    return f'https://{domain_or_url}'


def format_url_only(domain_or_url):
    """Return a single HTTPS URL line, or an empty string."""
    url = _https_url(domain_or_url)
    if not url:
        return ''
    return f'{url}\n'


def _default_url_lines(payload):
    """Return one HTTPS URL per line, sorted by AWS Region when applicable."""
    regional = payload.get('regionalEndpointUrls') or {}
    if regional:
        return ''.join(
            format_url_only(domain) for _, domain in sorted(regional.items())
        )
    return format_url_only(payload.get('endpointUrl', ''))


def emit_result(parsed_globals, payload, stdout=None):
    """Write command result to *stdout*, honoring --query and --output.

    By default, prints only the endpoint URLs. With --query or
    explicit --output, delegates to the standard CLI formatter.
    """
    if stdout is None:
        stdout = sys.stdout
    query = getattr(parsed_globals, 'query', None)
    explicit_output = getattr(parsed_globals, 'output', None)
    if query is None and not explicit_output:
        stdout.write(_default_url_lines(payload))
        stdout.flush()
        return
    # Drop empty fields so --no-wait results don't render blank rows.
    cleaned = {k: v for k, v in payload.items() if v}
    formatter = get_formatter(explicit_output or 'json', parsed_globals)
    formatter('deploy', cleaned, stdout)


_LAMBDA_WEB_ERROR_CODE = 'LambdaWebError'

_STRUCTURED_ERROR_FORMATS = ('json', 'yaml', 'text', 'table')


def _resolve_error_format(parsed_globals):
    fmt = getattr(parsed_globals, 'cli_error_format', None)
    return fmt.lower() if fmt else None


def emit_error(message, parsed_globals=None, stderr=None):
    """Render a lambda-web error, honoring ``--cli-error-format``.

    Structured formats emit a machine-readable document; default keeps
    the friendly ``Error: <message>`` line.
    """
    if stderr is None:
        stderr = sys.stderr
    fmt = _resolve_error_format(parsed_globals)
    if fmt in _STRUCTURED_ERROR_FORMATS:
        try:
            error_doc = {
                'Error': {
                    'Code': _LAMBDA_WEB_ERROR_CODE,
                    'Message': message,
                }
            }
            ns = argparse.Namespace(
                query=None, color=getattr(parsed_globals, 'color', 'off')
            )
            get_formatter(fmt, ns)('error', error_doc, stderr)
            return
        except Exception:
            # Never let a formatting problem swallow the error text.
            pass
    progress(f'Error: {message}', stderr=stderr)


def progress(message, stderr=None):
    """Write a progress message to *stderr*."""
    if stderr is None:
        stderr = sys.stderr
    stderr.write(f'{message}\n')
    stderr.flush()


def endpoint_url_fields(endpoint):
    """Return the URL fields of the deploy result for *endpoint*.

    A ``PerRegion`` endpoint is also addressable through one domain per Region,
    so those are surfaced as ``regionalEndpointUrls`` for ``--query`` to reach;
    otherwise the result would report one of N URLs and hide the rest. Keyed
    off the response rather than the endpoint type.
    """
    if not endpoint:
        return {'endpointUrl': ''}
    regional = {
        region: _https_url(data['domainName'])
        for region, data in (endpoint.get('regionalEndpoints') or {}).items()
        if data.get('domainName')
    }
    fields = {'endpointUrl': _https_url(endpoint.get('domainName', ''))}
    if regional:
        fields['regionalEndpointUrls'] = regional
    return fields


def report_regional_urls(endpoint):
    """Name the Region behind each URL on stderr, for a PerRegion endpoint.

    stdout stays a bare list of URLs for scripts to capture, so the
    Region -> URL mapping has to be reported somewhere else.
    """
    regional = endpoint_url_fields(endpoint).get('regionalEndpointUrls')
    if not regional:
        return
    listed = ', '.join(
        f'{region} -> {url}' for region, url in sorted(regional.items())
    )
    progress(f'PerRegion endpoint URLs ({len(regional)}): {listed}')


def emit_console_hint(parsed_globals, console):
    """Print the human 'Console: <url>' hint to stderr, when appropriate.

    Suppressed for ``--output json`` and ``--query``, where the caller is
    consuming the output programmatically.
    """
    if not console:
        return
    if getattr(parsed_globals, 'query', None) is not None:
        return
    if getattr(parsed_globals, 'output', None) == 'json':
        return
    progress('Console: ' + console)
