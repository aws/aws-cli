"""`s3 presign`'s URLs (upstream tests/functional/s3/test_presign_command.py).

Upstream freezes the clock in-process and compares each URL with a fixed
signature. A child process signs on the real clock, so each URL's
`X-Amz-Date` is checked against the time of the run and its signature is
recomputed for that date with upstream's keys. Each case first checks that
the recomputation at upstream's frozen date gives upstream's signature.
"""

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Final
from urllib.parse import urlsplit

import pytest

from apihelpers import ACCESS_KEY, REGION, SECRET_KEY, ApiSession

pytestmark = pytest.mark.asyncio

# The date upstream freezes `datetime.datetime.utcnow` at.
FROZEN_DATE: Final = "20160818T143303Z"
AMZ_DATE_FORMAT: Final = "%Y%m%dT%H%M%SZ"
# How far a URL's signing time may sit from the run's.
CLOCK_SLACK: Final = timedelta(minutes=5)
ALGORITHM: Final = "AWS4-HMAC-SHA256"
VIRTUAL_HOST: Final = f"bucket.s3.{REGION}.amazonaws.com"
PATH_HOST: Final = f"s3.{REGION}.amazonaws.com"


def query_params(query: str) -> dict[str, str]:
    """The URL's query, still encoded, as upstream splits it."""
    return dict(part.split("=", 1) for part in query.split("&"))


def credential(amz_date: str) -> str:
    return f"{ACCESS_KEY}%2F{amz_date[:8]}%2F{REGION}%2Fs3%2Faws4_request"


def hmac_sha256(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode(), hashlib.sha256).digest()


def presign_signature(
    host: str, path: str, expires: int, amz_date: str
) -> str:
    """The SigV4 query signature of a GET of `path` on `host` signed at
    `amz_date` with upstream's keys."""
    scope = f"{amz_date[:8]}/{REGION}/s3/aws4_request"
    query = (
        f"X-Amz-Algorithm={ALGORITHM}&X-Amz-Credential={credential(amz_date)}"
        f"&X-Amz-Date={amz_date}&X-Amz-Expires={expires}"
        "&X-Amz-SignedHeaders=host"
    )
    canonical_request = (
        f"GET\n{path}\n{query}\nhost:{host}\n\nhost\nUNSIGNED-PAYLOAD"
    )
    string_to_sign = (
        f"{ALGORITHM}\n{amz_date}\n{scope}\n"
        f"{hashlib.sha256(canonical_request.encode()).hexdigest()}"
    )
    key = f"AWS4{SECRET_KEY}".encode()
    for part in (amz_date[:8], REGION, "s3", "aws4_request"):
        key = hmac_sha256(key, part)
    return hmac.new(
        key, string_to_sign.encode(), hashlib.sha256
    ).hexdigest()


@pytest.mark.parametrize(
    ("args", "config", "host", "path", "expires", "frozen_signature"),
    [
        pytest.param(
            "s3://bucket/key",
            None,
            VIRTUAL_HOST,
            "/key",
            3600,
            "1297528058f2c8b89cfa52c6a47d6c54890700a1da24702b06d53e774c0acc95",
            id="generates-a-url",
        ),
        pytest.param(
            "s3://bucket.dots/key",
            None,
            PATH_HOST,
            "/bucket.dots/key",
            3600,
            "5a032639cabfe3db0b4b87ba3b12c29f5e42fe74cbba8a0eb69bfb30c6e2d277",
            id="non-dns-compatible-bucket",
        ),
        pytest.param(
            "s3://bucket/key --expires-in 1000",
            None,
            VIRTUAL_HOST,
            "/key",
            1000,
            "865fb61b021c3bf406c40d41353f584835fff1f158cf1b3e6ec06260ecbb8937",
            id="expires-in",
        ),
        pytest.param(
            "s3://bucket/key",
            "[default]\ns3 =\n    signature_version = s3v4\n",
            VIRTUAL_HOST,
            "/key",
            3600,
            "1297528058f2c8b89cfa52c6a47d6c54890700a1da24702b06d53e774c0acc95",
            id="sigv4-from-config",
        ),
        pytest.param(
            "bucket/key",
            None,
            VIRTUAL_HOST,
            "/key",
            3600,
            "1297528058f2c8b89cfa52c6a47d6c54890700a1da24702b06d53e774c0acc95",
            id="s3-prefix-not-needed",
        ),
        pytest.param(
            "s3://bucket/key",
            "[default]\ns3 =\n    addressing_style = path\n",
            PATH_HOST,
            "/bucket/key",
            3600,
            "c6dab3560db76aded03e6268338ddb0a6dec00ebc82d6e7abdc305529fcaba74",
            id="addressing-style-from-config",
        ),
    ],
)
async def test_presign_generates_signed_url(
    s3api: ApiSession,
    args: str,
    config: str | None,
    host: str,
    path: str,
    expires: int,
    frozen_signature: str,
) -> None:
    assert (
        presign_signature(host, path, expires, FROZEN_DATE)
        == frozen_signature
    )
    if config is not None:
        # Upstream's config file holds only this setting.
        s3api.config_path.write_text(config, encoding="utf-8")
    started = datetime.now(UTC)
    result = await s3api.run(f"s3 presign {args}")
    assert result.calls == (), result.describe()
    parts = urlsplit(result.stdout.strip())
    assert (parts.netloc, parts.path) == (host, path), result.describe()
    query = query_params(parts.query)
    amz_date = query.get("X-Amz-Date", "")
    signed_at = datetime.strptime(amz_date, AMZ_DATE_FORMAT).replace(
        tzinfo=UTC
    )
    assert started - CLOCK_SLACK <= signed_at <= started + CLOCK_SLACK
    assert query == {
        "X-Amz-Algorithm": ALGORITHM,
        "X-Amz-Credential": credential(amz_date),
        "X-Amz-Date": amz_date,
        "X-Amz-Expires": str(expires),
        "X-Amz-Signature": presign_signature(host, path, expires, amz_date),
        "X-Amz-SignedHeaders": "host",
    }, result.describe()
