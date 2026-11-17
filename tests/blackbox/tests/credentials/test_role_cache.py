from pathlib import Path
from typing import Final

import pytest

from credhelpers import (
    AMZ_DATE_PLACEHOLDER,
    CACHE_FILE_MODE,
    CLI_CACHE,
    SCOPE_DATE_PLACEHOLDER,
    RoleCacheContent,
    RouteKey,
    Sandbox,
    Stub,
    assert_signature,
    created_cache_directories,
    expected_request,
    export_credentials_output,
    role_cache_key,
    routed,
    run_export_credentials,
    sts_success_xml,
)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("sts_routes_through_proxy"),
]

# One run writes the assume-role cache (credentials.py:719-791, 830-850)
# through JSONFileCache (utils.py:3951-4017), and the next answers from it
# with a 400 tripwire behind every endpoint. What the writer leaves is
# what another tool sharing ~/.aws/cli/cache reads: the file name, its
# 0600 mode, and the Credentials members.
ACCOUNT: Final = "123456789012"
FUTURE_EXPIRATION: Final = "2099-01-01T00:00:00+00:00"
ROLE_ARN: Final = f"arn:aws:iam::{ACCOUNT}:role/r"
ROLE_SESSION_NAME: Final = "interop"
ASSUME_ROLE_CONFIG: Final = f"""\
[profile target]
role_arn = {ROLE_ARN}
role_session_name = {ROLE_SESSION_NAME}
source_profile = base

[profile base]
aws_access_key_id = AKIDBASE
aws_secret_access_key = BASE-secret
"""
STS_HOST: Final = "sts.us-east-1.amazonaws.com"
STS_ROUTE: Final[RouteKey] = ("POST", STS_HOST, "/")
ROLE_CACHE: Final = (
    Path("home")
    / CLI_CACHE
    / (
        role_cache_key(
            {"RoleArn": ROLE_ARN, "RoleSessionName": ROLE_SESSION_NAME}
        )
        + ".json"
    )
)
# AssumeRole with the source profile's keys, SigV4-signed for sts in
# us-east-1 and sent without a security token.
ROLE_REQUEST: Final = expected_request(
    "POST",
    STS_HOST,
    "/",
    body=(
        b"Action=AssumeRole&Version=2011-06-15&RoleSessionName=interop"
        b"&RoleArn=arn%3Aaws%3Aiam%3A%3A123456789012%3Arole%2Fr"
    ),
    headers={
        "authorization": "AWS4-HMAC-SHA256",
        "x-amz-date": AMZ_DATE_PLACEHOLDER,
        "content-type": "application/x-www-form-urlencoded",
    },
    signing_scope=("AKIDBASE", SCOPE_DATE_PLACEHOLDER, "us-east-1", "sts"),
)
# The account comes from the AssumedRoleUser ARN (credentials.py:852-859)
# and Expiration is serialized with isoformat().
ROLE_CACHED: Final = RoleCacheContent(
    {
        "Credentials": {
            "AccessKeyId": "AKIDROLE",
            "SecretAccessKey": "ROLE-secret",
            "SessionToken": "ROLE-token",
            "Expiration": FUTURE_EXPIRATION,
            "AccountId": ACCOUNT,
        }
    }
)
EXPORTED: Final = export_credentials_output(
    "AKIDROLE", "ROLE-secret", "ROLE-token", FUTURE_EXPIRATION
)


async def test_cache_written_by_one_run_is_read_by_next_without_requests(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    server, proxy = stub
    sandbox.config.write_text(ASSUME_ROLE_CONFIG, encoding="utf-8")
    script = {STS_ROUTE: [sts_success_xml()]}

    writer = await run_export_credentials(
        aws_cli,
        sandbox,
        [server],
        sandbox.env(proxy),
        globals_=("--profile", "target"),
        handlers={server: lambda: routed(script)},
    )

    assert (writer.returncode, writer.stdout, writer.stderr) == (
        0,
        EXPORTED,
        b"",
    ), writer.describe()
    assert writer.requests == (ROLE_REQUEST,), writer.describe()
    assert_signature(writer.raw_requests[0], "AKIDBASE", "BASE-secret")
    assert writer.changes == {
        **created_cache_directories(),
        ROLE_CACHE.as_posix(): (CACHE_FILE_MODE, ROLE_CACHED),
    }, writer.describe()
    sandbox.seal()

    reader = await run_export_credentials(
        aws_cli,
        sandbox,
        [server],
        sandbox.env(proxy),
        globals_=("--profile", "target"),
        handlers={server: lambda: routed({})},
    )

    assert (reader.returncode, reader.stdout, reader.stderr) == (
        0,
        EXPORTED,
        b"",
    ), reader.describe()
    assert reader.requests == (), reader.describe()
    assert reader.changes == {}, reader.describe()
