from awscli import __version__ as awscli_version
from tests import CLIRunner
from tests.functional.botocore.test_useragent import (
    parse_registered_feature_ids,
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
