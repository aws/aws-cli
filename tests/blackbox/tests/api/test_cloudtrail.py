"""CloudTrail commands (upstream tests/functional/cloudtrail)."""

import binascii
import calendar
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Final

import pytest
from awscrt.crypto import RSA, RSASignatureAlgorithm

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio

# The fingerprint and DER key (base64) of upstream's sample key pair, which
# signed its test_resource exports.
SAMPLE_PUBLIC_KEY_FINGERPRINT: Final = "67b9fa73676d86966b449dd677850753"
SAMPLE_PUBLIC_KEY: Final = (
    "MIIBCgKCAQEA1OxVzcylHnxhysU41BcHucQn47bywceJEPkze53R"
    "ZUaYtvTAXYf0ONbdk/yQ8c5Bq6l5nL0qjT1UNhVfccCsTaToL58w"
    "PePg9U29D+MtiQXz6yecW7Rzs5rP5i4EU2YDPoYaphIVowYZjkHy"
    "C72L/2lQ/Q5rSotIjUdCq6Wv6i7bFHLiCNtgP95xfL9pxytAyGdC"
    "zHDBJb/H60x7q/wqO6/HaZI38aY7piHqazd2vpaNxPShHyvpdR0P"
    "29tNFxo+5V4VVW2/QC1/QLTLLAzQNiO+ZOpsHa8rgYmPv0YI4sFA"
    "9vFhHyUdh9skopO7Jg/gAjAdtzuLCnXpfuwQ/+EXnQIDAQAB"
)
SAMPLE_HASH_VALUE: Final = (
    "3b9c358f36f0a31b6ad3e14f309c7cf198ac9246e8316f9ce543d5b19ac02b80"
)
SAMPLE_S3_BUCKET_NAME: Final = "lake-bucket-name"
SAMPLE_S3_EXPORT_FILE_PREFIX: Final = "lake-export-prefix/"
VALIDATED: Final = "Successfully validated sign and query result files\n"


def epoch(timestamp: str) -> int:
    return calendar.timegm(
        datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").timetuple()
    )


@pytest.fixture
def sample_export(pytestconfig: pytest.Config) -> Path:
    """Upstream's sample export: its sign file, result file, and key."""
    # run.py roots pytest at the aws-cli source tree.
    return (
        pytestconfig.rootpath
        / "tests"
        / "functional"
        / "cloudtrail"
        / "test_resource"
    )


async def test_verify_local_export_succeeds(
    api: ApiSession, sample_export: Path
) -> None:
    result = await api.run(
        [
            "cloudtrail",
            "verify-query-results",
            f"--local-export-path={sample_export}",
        ],
        replies=[
            {
                "PublicKeyList": [
                    {
                        "Fingerprint": SAMPLE_PUBLIC_KEY_FINGERPRINT,
                        "Value": SAMPLE_PUBLIC_KEY,
                    }
                ]
            }
        ],
    )
    assert VALIDATED in result.stdout
    # The keys valid from the sign file's query completion time on.
    assert result.operations_with_params == [
        (
            "ListPublicKeys",
            {
                "StartTime": epoch("2022-05-10T22:06:30Z"),
                "EndTime": epoch("2022-05-30T22:06:30Z"),
            },
        )
    ]


async def test_verify_s3_export_with_incorrect_hash_fails(
    api: ApiSession, sample_export: Path
) -> None:
    private_key = RSA.new_private_key_from_pem_data(
        (sample_export / "sample_private_key.pem").read_bytes()
    )
    signature = private_key.sign(
        signature_algorithm=RSASignatureAlgorithm.PKCS1_5_SHA256,
        digest=hashlib.sha256(SAMPLE_HASH_VALUE.encode()).digest(),
    )
    sign_file = {
        "region": "us-east-1",
        "files": [
            {
                "fileHashValue": SAMPLE_HASH_VALUE,
                "fileName": "result_1.csv.gz",
            }
        ],
        "hashAlgorithm": "SHA-256",
        "publicKeyFingerprint": "fingerprint",
        "signatureAlgorithm": "SHA256withRSA",
        "hashSignature": binascii.hexlify(signature).decode(),
        "queryCompleteTime": "2022-05-10T22:06:30Z",
    }
    public_key = (sample_export / "sample_public_key.der").read_bytes()
    result = await api.run(
        "cloudtrail verify-query-results"
        f" --s3-bucket={SAMPLE_S3_BUCKET_NAME}"
        f" --s3-prefix={SAMPLE_S3_EXPORT_FILE_PREFIX}",
        replies=[
            {"Body": json.dumps(sign_file).encode()},
            # The result file's bytes do not hash to the recorded value.
            {"Body": b"123"},
            {
                "PublicKeyList": [
                    # The DER key, which the wire carries in base64.
                    {"Fingerprint": "fingerprint", "Value": public_key}
                ]
            },
        ],
        expected_rc=255,
    )
    assert (
        "has inconsistent hash value with hash value recorded"
        in result.stderr
    )
    # botocore sets ChecksumMode after upstream's hook copies the
    # parameters.
    assert result.operations_with_params == [
        (
            "GetObject",
            {
                "Bucket": SAMPLE_S3_BUCKET_NAME,
                "Key": "lake-export-prefix/result_sign.json",
                "ChecksumMode": "ENABLED",
            },
        ),
        (
            "GetObject",
            {
                "Bucket": SAMPLE_S3_BUCKET_NAME,
                "Key": "lake-export-prefix/result_1.csv.gz",
                "ChecksumMode": "ENABLED",
            },
        ),
    ]


@pytest.mark.parametrize(
    ("args", "message"),
    [
        pytest.param(
            "",
            "Require parameter --s3-bucket or --local-export-path.",
            id="both-empty",
        ),
        pytest.param(
            " --s3-bucket=test-bucket --local-export-path=/test/",
            "Parameter --local-export-path can not be specified with"
            " parameter --s3-bucket nor --s3-prefix.",
            id="both-provided",
        ),
    ],
)
async def test_verify_rejects_invalid_parameters(
    api: ApiSession, args: str, message: str
) -> None:
    result = await api.run(
        "cloudtrail verify-query-results" + args, expected_rc=252
    )
    assert message in result.stderr
    assert result.calls == ()
