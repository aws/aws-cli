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
import io
import json

import jmespath
import pytest

from awscli.customizations.lambdaweb.output import (
    console_url,
    emit_console_hint,
    emit_error,
    emit_result,
    endpoint_url_fields,
    format_url_only,
    progress,
)

_FULL_PAYLOAD = {
    'functionArn': 'arn:aws:lambda:us-east-1:123456789012:function:my-app',
    'endpointUrl': 'https://abc123.lambda-url.us-east-1.on.aws',
    'roleArn': 'arn:aws:iam::123456789012:role/awscli-lambdaweb-my-app',
    'bucketName': 'awscli-lambdaweb-123456789012-us-east-1',
    'objectKey': 'my-app/deploy-abc123.zip',
    'consoleUrl': 'https://us-east-1.console.aws.amazon.com/lambda/home#/web-functions/my-app',
}


def test_format_url_only_trailing_newline():
    result = format_url_only('abc123.lambda-url.us-east-1.on.aws')
    assert result == 'https://abc123.lambda-url.us-east-1.on.aws\n'
    assert result.endswith('\n')


def test_format_url_only_does_not_duplicate_scheme():
    result = format_url_only('https://abc123.lambda-url.us-east-1.on.aws')
    assert result == 'https://abc123.lambda-url.us-east-1.on.aws\n'


def _globals(output=None, query=None, color='off'):
    """A parsed-globals namespace shaped like the real CLI globals."""
    return argparse.Namespace(output=output, query=query, color=color)


def test_emit_result_default_prints_url_only():
    # No --query and no explicit --output: the friendly "here's your URL"
    # default (not a JSON blob).
    stdout = io.StringIO()
    emit_result(_globals(), _FULL_PAYLOAD, stdout=stdout)
    assert stdout.getvalue() == 'https://abc123.lambda-url.us-east-1.on.aws\n'


def test_emit_result_json_mode_writes_json():
    stdout = io.StringIO()
    emit_result(_globals(output='json'), _FULL_PAYLOAD, stdout=stdout)
    parsed = json.loads(stdout.getvalue())
    for key in (
        'functionArn',
        'endpointUrl',
        'roleArn',
        'bucketName',
        'objectKey',
        'consoleUrl',
    ):
        assert key in parsed


def test_emit_result_explicit_text_uses_standard_formatter():
    # An EXPLICIT --output text routes through the standard CLI text formatter
    # (all fields), like every other command -- not the url-only shortcut.
    stdout = io.StringIO()
    emit_result(_globals(output='text'), _FULL_PAYLOAD, stdout=stdout)
    out = stdout.getvalue()
    assert _FULL_PAYLOAD['functionArn'] in out
    assert _FULL_PAYLOAD['roleArn'] in out


def test_emit_result_query_honored_in_text():
    # --query endpointUrl --output text returns ONLY the queried field.
    stdout = io.StringIO()
    pg = _globals(output='text', query=jmespath.compile('endpointUrl'))
    emit_result(pg, _FULL_PAYLOAD, stdout=stdout)
    assert stdout.getvalue() == 'https://abc123.lambda-url.us-east-1.on.aws\n'


def test_emit_result_query_defaults_output_to_json():
    # --query with no explicit --output still formats (defaults to json) rather
    # than falling back to the url-only shortcut.
    stdout = io.StringIO()
    pg = _globals(query=jmespath.compile('roleArn'))
    emit_result(pg, _FULL_PAYLOAD, stdout=stdout)
    assert _FULL_PAYLOAD['roleArn'] in stdout.getvalue()


def test_emit_result_omits_empty_fields():
    # --no-wait leaves endpointUrl empty; it should be dropped, not rendered
    # as an empty value.
    stdout = io.StringIO()
    payload = dict(_FULL_PAYLOAD, endpointUrl='')
    emit_result(_globals(output='json'), payload, stdout=stdout)
    parsed = json.loads(stdout.getvalue())
    assert 'endpointUrl' not in parsed
    assert 'functionArn' in parsed


def test_emit_error_default_is_friendly_line():
    stderr = io.StringIO()
    ns = argparse.Namespace(cli_error_format=None, color='off')

    emit_error('something broke', ns, stderr=stderr)
    assert stderr.getvalue() == 'Error: something broke\n'


def test_emit_error_json_is_structured():
    stderr = io.StringIO()
    ns = argparse.Namespace(cli_error_format='json', color='off')

    emit_error('something broke', ns, stderr=stderr)
    doc = json.loads(stderr.getvalue())
    assert doc['Error']['Message'] == 'something broke'
    assert doc['Error']['Code'] == 'LambdaWebError'


def test_emit_error_none_globals_is_safe():
    stderr = io.StringIO()

    emit_error('boom', None, stderr=stderr)
    assert stderr.getvalue() == 'Error: boom\n'


def test_progress_writes_only_to_stderr():
    stderr = io.StringIO()
    progress('Deploying function...', stderr=stderr)
    assert stderr.getvalue() == 'Deploying function...\n'


def test_console_url_aws_partition():
    assert (
        console_url('aws', 'us-west-2', 'lwtest')
        == 'https://us-west-2.console.aws.amazon.com/lambda/home#/web-functions/lwtest'
    )


def test_console_url_china_partition():
    assert (
        console_url('aws-cn', 'cn-north-1', 'lwtest')
        == 'https://cn-north-1.console.amazonaws.cn/lambda/home#/web-functions/lwtest'
    )


def test_console_url_govcloud_partition():
    assert (
        console_url('aws-us-gov', 'us-gov-west-1', 'lwtest')
        == 'https://us-gov-west-1.console.amazonaws-us-gov.com/lambda/home#/web-functions/lwtest'
    )


@pytest.mark.parametrize('partition', ['aws-iso', 'aws-iso-b', 'unknown'])
def test_console_url_unknown_partition_is_empty(partition):
    assert console_url(partition, 'us-iso-east-1', 'lwtest') == ''


def test_emit_console_hint_omits_empty_url(capsys):
    emit_console_hint(_globals(), '')
    assert capsys.readouterr().err == ''


def test_console_url_raises_on_empty_inputs():
    with pytest.raises(ValueError):
        console_url('', 'us-west-2', 'lwtest')
    with pytest.raises(ValueError):
        console_url('aws', '', 'lwtest')
    with pytest.raises(ValueError):
        console_url('aws', 'us-west-2', '')


# ---------------------------------------------------------------------------
# PerRegion endpoints: one addressable URL per Region
# ---------------------------------------------------------------------------

_PER_REGION_PAYLOAD = dict(
    _FULL_PAYLOAD,
    endpointUrl='https://d81c50sg58.bz3.lambda-web.us-east-1.on.aws',
    regionalEndpointUrls={
        # deliberately not in sorted order, to pin the sort
        'us-west-2': 'https://d81c50sg58.bz3.lambda-web.us-west-2.on.aws',
        'us-east-1': 'https://d81c50sg58.bz3.lambda-web.us-east-1.on.aws',
    },
)


def test_emit_result_default_prints_every_regional_url():
    """A PerRegion deploy prints all its URLs, Region-sorted, one per line.

    endpointUrl is only the home Region's domain, so printing just that would
    hide the other Regions' URLs entirely.
    """
    stdout = io.StringIO()
    emit_result(_globals(), _PER_REGION_PAYLOAD, stdout=stdout)
    assert stdout.getvalue() == (
        'https://d81c50sg58.bz3.lambda-web.us-east-1.on.aws\n'
        'https://d81c50sg58.bz3.lambda-web.us-west-2.on.aws\n'
    )


def test_emit_result_default_regional_urls_are_bare_lines():
    """stdout stays capturable: only URLs, no Region labels or prose."""
    stdout = io.StringIO()
    emit_result(_globals(), _PER_REGION_PAYLOAD, stdout=stdout)
    for line in stdout.getvalue().splitlines():
        assert line.startswith('https://')
        assert ' ' not in line


def test_emit_result_regional_urls_reachable_by_query():
    stdout = io.StringIO()
    pg = _globals(
        output='text',
        query=jmespath.compile('regionalEndpointUrls."us-west-2"'),
    )
    emit_result(pg, _PER_REGION_PAYLOAD, stdout=stdout)
    assert (
        stdout.getvalue()
        == 'https://d81c50sg58.bz3.lambda-web.us-west-2.on.aws\n'
    )


def test_emit_result_regional_urls_present_in_json():
    stdout = io.StringIO()
    emit_result(_globals(output='json'), _PER_REGION_PAYLOAD, stdout=stdout)
    parsed = json.loads(stdout.getvalue())
    assert parsed['regionalEndpointUrls'] == {
        'us-east-1': 'https://d81c50sg58.bz3.lambda-web.us-east-1.on.aws',
        'us-west-2': 'https://d81c50sg58.bz3.lambda-web.us-west-2.on.aws',
    }


def test_endpoint_url_fields_returns_complete_urls():
    endpoint = {
        'domainName': 'global.lambda-web.example.com',
        'regionalEndpoints': {
            'us-east-1': {
                'domainName': 'east.lambda-web.example.com',
            }
        },
    }

    assert endpoint_url_fields(endpoint) == {
        'endpointUrl': 'https://global.lambda-web.example.com',
        'regionalEndpointUrls': {
            'us-east-1': 'https://east.lambda-web.example.com'
        },
    }


def test_emit_result_single_url_unchanged_without_regional():
    """Endpoint types with one domain keep the exact previous output."""
    stdout = io.StringIO()
    emit_result(_globals(), _FULL_PAYLOAD, stdout=stdout)
    assert stdout.getvalue() == 'https://abc123.lambda-url.us-east-1.on.aws\n'


def test_emit_result_no_wait_still_prints_nothing():
    """--no-wait has neither a domain nor regional domains: no bogus line."""
    stdout = io.StringIO()
    payload = dict(_FULL_PAYLOAD, endpointUrl='')
    payload.pop('regionalEndpointUrls', None)
    emit_result(_globals(), payload, stdout=stdout)
    assert stdout.getvalue() == ''
