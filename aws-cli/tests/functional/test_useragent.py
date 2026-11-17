import pytest

from awscli import __version__ as awscli_version
from awscli.testutils import mock
from tests import CLIRunner, HTTPResponse
from tests.functional.botocore.test_useragent import (
    get_captured_ua_strings,
    parse_registered_feature_ids,
)
from tests.functional.s3 import (
    FakeCRTFuture,
    FakeCRTS3Request,
    IgnoreCRTRequestsSessionStubber,
)


def assert_expected_user_agent(result, service, operation):
    ua_string = result.aws_requests[0].http_requests[0].headers['User-Agent']
    assert ua_string.startswith(f'aws-cli/{awscli_version}')
    assert ' md/installer#' in ua_string
    assert ' md/awscrt#' in ua_string
    assert ' md/arch#' in ua_string
    assert ' md/prompt#off' in ua_string
    assert f' md/command#{service}.{operation}' in ua_string
    assert ' ua/2.1 ' in ua_string
    assert ' os/' in ua_string
    assert ' lang/python' in ua_string
    assert ' cfg/' in ua_string
    assert f' md/command#{service}.{operation}' in ua_string


def test_basic_user_agent():
    cli_runner = CLIRunner()
    service = 'sts'
    operation = 'get-caller-identity'
    result = cli_runner.run([service, operation])
    assert_expected_user_agent(result, service, operation)


def test_user_agent_for_customization():
    cli_runner = CLIRunner()
    service = 's3'
    operation = 'ls'
    result = cli_runner.run([service, operation])
    assert_expected_user_agent(result, service, operation)
    ua_string = result.aws_requests[0].http_requests[0].headers['User-Agent']
    feature_list = parse_registered_feature_ids(ua_string)
    assert 'C' in feature_list


def test_user_agent_reports_classic_transfer_client_for_s3_copy():
    cli_runner = CLIRunner()
    cli_runner.add_response(
        HTTPResponse(
            headers={
                'Content-Length': '100',
                'Last-Modified': 'Mon, 1 Jan 2024 00:00:00 GMT',
                'ETag': '"etag"',
            }
        )
    )
    cli_runner.add_response(
        HTTPResponse(body='<CopyObjectResult></CopyObjectResult>')
    )
    # S3 to S3 copies always auto resolve to the classic transfer client.
    result = cli_runner.run(
        ['s3', 'cp', 's3://bucket/key', 's3://other-bucket/key']
    )
    assert result.rc == 0
    ua_string = result.aws_requests[0].http_requests[0].headers['User-Agent']
    feature_list = parse_registered_feature_ids(ua_string)
    assert 'Af' in feature_list


def _complete_crt_request(*args, **kwargs):
    s3_request = FakeCRTS3Request(future=FakeCRTFuture(kwargs.get('on_done')))
    # Completing the future invokes on_done, which finishes the transfer.
    s3_request.finished_future.result()
    return s3_request


@pytest.fixture
def mock_crt_s3_client():
    with mock.patch('s3transfer.crt.S3Client') as mock_client:
        mock_client.return_value.make_request.side_effect = (
            _complete_crt_request
        )
        yield mock_client


@pytest.fixture
def mock_crt_process_lock(monkeypatch):
    # Hold a fresh, mocked lock so another process running the crt client
    # cannot make auto resolution fall back to the classic transfer client.
    monkeypatch.setattr('s3transfer.crt.CRT_S3_PROCESS_LOCK', None)
    with mock.patch('awscrt.s3.CrossProcessLock', spec=True) as mock_lock:
        yield mock_lock


def test_user_agent_reports_auto_resolved_crt_transfer_client(
    tmp_path, mock_crt_s3_client, mock_crt_process_lock
):
    upload = tmp_path / 'foo.txt'
    upload.write_text('contents')
    cli_runner = CLIRunner(session_stubber=IgnoreCRTRequestsSessionStubber())
    with mock.patch('awscrt.s3.is_optimized_for_system', return_value=False):
        result = cli_runner.run(['s3', 'cp', str(upload), 's3://bucket/key'])
    assert result.rc == 0, result.stderr
    make_request_kwargs = (
        mock_crt_s3_client.return_value.make_request.call_args[1]
    )
    ua_string = make_request_kwargs['request'].headers.get('User-Agent')
    feature_list = parse_registered_feature_ids(ua_string)
    assert 'Ag' in feature_list
