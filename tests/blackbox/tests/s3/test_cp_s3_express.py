"""`s3 cp --recursive --case-conflict` from an S3 Express directory bucket
(upstream tests/functional/s3/test_cp_command.py, TestS3ExpressCpRecursive).

The command cannot detect case conflicts in a directory bucket's listing,
whose keys are not in order, so it refuses `error` and `skip` and warns
for `warn`. Each client the command builds opens its own session with
CreateSession before its first request. awswire decodes a directory
bucket's object requests as requests on a bucket named by the key, so
these tests compare each request's method, host, and path.
"""

import platform
from typing import Final

import pytest
from localstub import HTTPResponse

from apihelpers import ApiSession, CommandRun

pytestmark = pytest.mark.asyncio

BUCKET: Final = "bucket--usw2-az1--x-s3"
HOST: Final = f"{BUCKET}.s3express-usw2-az1.us-east-1.amazonaws.com"
BODY: Final = b"foo"


def xml(body: str) -> HTTPResponse:
    return HTTPResponse.raw(
        body.encode(), headers={"Content-Type": "application/xml"}
    )


def create_session() -> HTTPResponse:
    return xml(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CreateSessionResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        "<Credentials><SessionToken>TOKEN</SessionToken>"
        "<SecretAccessKey>SECRET</SecretAccessKey>"
        "<AccessKeyId>AKID</AccessKeyId>"
        "<Expiration>2099-01-01T00:00:00Z</Expiration></Credentials>"
        "</CreateSessionResult>"
    )


def list_objects(keys: list[str]) -> HTTPResponse:
    # Each listed Size is the body served.
    contents = "".join(
        f"<Contents><Key>{key}</Key>"
        "<LastModified>2015-12-08T18:26:43.000Z</LastModified>"
        f'<Size>{len(BODY)}</Size><ETag>"foo-1"</ETag></Contents>'
        for key in keys
    )
    return xml(
        '<?xml version="1.0" ?>'
        '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        f"<Prefix/>{contents}</ListBucketResult>"
    )


def get_object() -> HTTPResponse:
    return HTTPResponse.raw(
        BODY,
        headers={
            "ETag": '"foo-1"',
            "Content-Length": str(len(BODY)),
            "Last-Modified": "Thu, 11 Feb 2021 04:24:23 GMT",
        },
    )


def sent(run: CommandRun) -> list[tuple[str, str, str]]:
    return [
        (
            call.request.method,
            call.request.headers.get("host", ""),
            call.request.effective_path,
        )
        for call in run.calls
    ]


@pytest.mark.parametrize("mode", ["error", "skip"])
async def test_s3_express_rejects_case_conflict_mode(
    s3api: ApiSession, mode: str
) -> None:
    run = await s3api.run(
        [
            "s3",
            "cp",
            "--recursive",
            f"s3://{BUCKET}",
            str(s3api.cwd),
            "--case-conflict",
            mode,
        ],
        expected_rc=252,
    )
    assert f"`{mode}` is not a valid value" in run.stderr, run.describe()
    assert run.calls == (), run.describe()


@pytest.mark.skipif(
    platform.system() not in ("Darwin", "Linux"),
    reason="Can't rename to same file",
)
async def test_s3_express_warn_emits_warning(s3api: ApiSession) -> None:
    run = await s3api.run(
        [
            "s3",
            "cp",
            "--recursive",
            f"s3://{BUCKET}",
            str(s3api.cwd),
            "--case-conflict",
            "warn",
        ],
        replies=[
            create_session(),
            list_objects(["a.txt", "A.txt"]),
            create_session(),
            get_object(),
            get_object(),
        ],
    )
    assert "warning: Recursive copies/moves" in run.stderr, run.describe()
    # The listing's client, then the transfers' client, opens a session.
    calls = sent(run)
    assert calls[:3] == [
        ("GET", HOST, "/?session"),
        ("GET", HOST, "/?list-type=2&prefix=&encoding-type=url"),
        ("GET", HOST, "/?session"),
    ], run.describe()
    # The two downloads run at once, so either may arrive first.
    assert sorted(calls[3:]) == [
        ("GET", HOST, "/A.txt"),
        ("GET", HOST, "/a.txt"),
    ], run.describe()
    # A case-insensitive filesystem holds the two as one file.
    assert {path.read_bytes() for path in s3api.cwd.iterdir()} == {BODY}
