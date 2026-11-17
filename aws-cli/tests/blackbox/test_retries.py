"""Blackbox tests for default retry behavior.

These verify, end to end against the CLI binary, how many attempts the
default (standard) retry mode makes when a service keeps returning a
retryable error, including service-specific max attempts.
"""

from __future__ import annotations

import json

import pytest
from localstub.server import HTTPResponse

from tests.blackbox.utils import (
    cli_env,
    error_response,
    format_requests,
    mock_server,
    run_cli,
)


def _default_retry_env(proxy) -> dict[str, str]:
    # cli_env() pins AWS_MAX_ATTEMPTS=1; drop it so the CLI uses its
    # defaults for both retry mode and max attempts.
    env = cli_env(proxy)
    env.pop("AWS_MAX_ATTEMPTS", None)
    env.pop("AWS_RETRY_MODE", None)
    return env


def _json_error_response(error_type: str, status: int) -> HTTPResponse:
    body = json.dumps(
        {
            "__type": f"com.amazonaws.dynamodb.v20120810#{error_type}",
            "message": "Test error",
        }
    ).encode()
    return HTTPResponse.raw(
        body,
        status=status,
        headers={"Content-Type": "application/x-amz-json-1.0"},
    )


def _assert_attempts(server, stderr: bytes, expected_attempts: int) -> None:
    assert len(server.requests) == expected_attempts, format_requests(server)
    assert b"reached max retries" in stderr, stderr.decode()
    for i, request in enumerate(server.requests, start=1):
        assert request.headers.get("amz-sdk-request").startswith(
            f"attempt={i}; max={expected_attempts}"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "args, response, expected_attempts",
    [
        pytest.param(
            ["dynamodb", "list-tables"],
            _json_error_response("ThrottlingException", 429),
            4,
            id="dynamodb-throttling",
        ),
        pytest.param(
            ["dynamodb", "list-tables"],
            _json_error_response("ServiceUnavailable", 503),
            4,
            id="dynamodb-transient",
        ),
        pytest.param(
            ["s3api", "list-buckets"],
            error_response(
                code="SlowDown",
                message="Please reduce your request rate.",
                status=429,
            ),
            3,
            id="s3-throttling",
        ),
        pytest.param(
            ["s3api", "list-buckets"],
            error_response(
                code="InternalError",
                message="Internal Server Error",
                status=500,
            ),
            3,
            id="s3-transient",
        ),
    ],
)
async def test_default_max_attempts(
    aws_cli: str, args, response, expected_attempts
) -> None:
    async with mock_server() as (server, proxy):
        server.set_default_response(response)
        _, stderr, rc = await run_cli(
            aws_cli, args, _default_retry_env(proxy)
        )

    assert rc != 0, stderr.decode()
    _assert_attempts(server, stderr, expected_attempts)


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["env", "config"])
async def test_configured_max_attempts_overrides_service_default(
    aws_cli: str, aws_config, source: str
) -> None:
    async with mock_server() as (server, proxy):
        server.set_default_response(
            _json_error_response("ServiceUnavailable", 503)
        )
        env = _default_retry_env(proxy)
        if source == "env":
            env["AWS_MAX_ATTEMPTS"] = "5"
        else:
            env["AWS_CONFIG_FILE"] = aws_config(
                {"default": {"max_attempts": "5"}}
            )
        _, stderr, rc = await run_cli(
            aws_cli, ["dynamodb", "list-tables"], env
        )

    assert rc != 0, stderr.decode()
    _assert_attempts(server, stderr, 5)
