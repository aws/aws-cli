"""CloudFront commands (upstream tests/functional/cloudfront)."""

import base64
import json
import re
from pathlib import Path
from typing import Any, Final
from urllib.parse import parse_qs, urlsplit

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio


class Matching:
    """Equal to any string the pattern matches in full: the customizations'
    unique strings join a prefix, the time, and a random number."""

    def __init__(self, pattern: str) -> None:
        self.pattern = re.compile(pattern)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, str) and bool(self.pattern.fullmatch(other))

    def __hash__(self) -> int:
        return hash(self.pattern)

    def __repr__(self) -> str:
        return f"Matching({self.pattern.pattern!r})"


def unique_string(prefix: str) -> Matching:
    return Matching(rf"{re.escape(prefix)}-\d+-\d+")


CREATE_DISTRIBUTION: Final = "cloudfront create-distribution "
UPDATE_DISTRIBUTION: Final = "cloudfront update-distribution --id myid "
# The --origin-domain-name template's cache behavior, which targets the one
# origin it adds.
TEMPLATE_CACHE_BEHAVIOR: Final = {
    "ForwardedValues": {
        "QueryString": False,
        "Cookies": {"Forward": "none"},
    },
    "TrustedSigners": {"Enabled": False, "Quantity": 0},
    "ViewerProtocolPolicy": "allow-all",
    "MinTTL": 0,
}
SHORTHAND_CONFIG: Final = (
    "--distribution-config "
    "Origins={Quantity=1,Items=[{Id=foo,DomainName=bar}]},"
    "DefaultCacheBehavior={"
    "TargetOriginId=foo,"
    "ForwardedValues={QueryString=False,Cookies={Forward=none}},"
    "TrustedSigners={Enabled=True,Quantity=0},"
    "ViewerProtocolPolicy=allow-all,"
    "MinTTL=0"
    "},"
    "CallerReference=abcd,"
    "Enabled=True,"
    "Comment="
)
SHORTHAND_CACHE_BEHAVIOR: Final = {
    "TargetOriginId": "foo",
    "ForwardedValues": {"QueryString": False, "Cookies": {"Forward": "none"}},
    "TrustedSigners": {"Enabled": True, "Quantity": 0},
    "ViewerProtocolPolicy": "allow-all",
    "MinTTL": 0,
}
SHORTHAND_DISTRIBUTION_CONFIG: Final = {
    "Origins": {
        "Quantity": 1,
        "Items": [{"Id": "foo", "DomainName": "bar"}],
    },
    "CallerReference": "abcd",
    "Comment": "",
    "Enabled": True,
    "DefaultCacheBehavior": SHORTHAND_CACHE_BEHAVIOR,
}
CUSTOM_ORIGIN: Final = {
    "CustomOriginConfig": {
        "HTTPPort": 80,
        "HTTPSPort": 443,
        "OriginProtocolPolicy": "http-only",
    }
}
S3_ORIGIN: Final = {"S3OriginConfig": {"OriginAccessIdentity": ""}}


@pytest.mark.parametrize(
    ("args", "domain", "origin_config", "root_object"),
    [
        pytest.param(
            "--origin-domain-name foo.com",
            "foo.com",
            CUSTOM_ORIGIN,
            {},
            id="custom-domain",
        ),
        pytest.param(
            "--origin-domain-name foo.s3.amazonaws.com",
            "foo.s3.amazonaws.com",
            S3_ORIGIN,
            {},
            id="s3-domain",
        ),
        pytest.param(
            "--origin-domain-name foo.s3.amazonaws.com"
            " --default-root-object index.html",
            "foo.s3.amazonaws.com",
            S3_ORIGIN,
            {"DefaultRootObject": "index.html"},
            id="s3-domain-with-default-root-object",
        ),
    ],
)
async def test_create_distribution_builds_config_from_origin_domain_name(
    api: ApiSession,
    args: str,
    domain: str,
    origin_config: dict[str, Any],
    root_object: dict[str, str],
) -> None:
    result = await api.run(CREATE_DISTRIBUTION + args)
    assert result.last_params is not None
    origins = result.last_params["DistributionConfig"]["Origins"]
    origin_id = origins["Items"][0]["Id"]
    assert origin_id == unique_string(domain)
    assert result.last_params == {
        "DistributionConfig": {
            "Origins": {
                "Quantity": 1,
                "Items": [
                    {
                        **origin_config,
                        "DomainName": domain,
                        "Id": origin_id,
                        "OriginPath": "",
                    }
                ],
            },
            "CallerReference": unique_string("cli"),
            "Comment": "",
            "Enabled": True,
            "DefaultCacheBehavior": {
                **TEMPLATE_CACHE_BEHAVIOR,
                "TargetOriginId": origin_id,
            },
            **root_object,
        },
    }


async def test_create_distribution_accepts_distribution_config(
    api: ApiSession,
) -> None:
    await api.assert_params_for_cmd(
        CREATE_DISTRIBUTION + SHORTHAND_CONFIG,
        {"DistributionConfig": SHORTHAND_DISTRIBUTION_CONFIG},
    )


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(
            CREATE_DISTRIBUTION
            + "--distribution-config {} --origin-domain-name a.us",
            id="create-distribution",
        ),
        pytest.param(
            UPDATE_DISTRIBUTION
            + "--distribution-config {} --default-root-object foo",
            id="update-distribution",
        ),
    ],
)
async def test_distribution_config_excludes_its_shortcuts(
    api: ApiSession, command: str
) -> None:
    result = await api.assert_params_for_cmd(
        command,
        expected_rc=252,
        stderr_contains="cannot be specified when one of the following",
    )
    assert result.calls == ()


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(CREATE_DISTRIBUTION, id="create-distribution"),
        pytest.param(UPDATE_DISTRIBUTION, id="update-distribution"),
        pytest.param(
            "cloudfront create-invalidation --distribution-id my_id",
            id="create-invalidation",
        ),
        pytest.param(
            "cloudfront create-invalidation --distribution-id my_id"
            " --invalidation-batch {} --paths foo",
            id="create-invalidation-batch-and-paths",
        ),
    ],
)
async def test_command_without_its_input_is_rejected(
    api: ApiSession, command: str
) -> None:
    result = await api.run(command, expected_rc=252)
    assert result.calls == ()


async def test_create_invalidation_sends_invalidation_batch(
    api: ApiSession,
) -> None:
    await api.assert_params_for_cmd(
        "cloudfront create-invalidation --distribution-id my_id"
        " --invalidation-batch"
        " Paths={Quantity=2,Items=[foo.txt,bar.txt]},CallerReference=ab",
        {
            "DistributionId": "my_id",
            "InvalidationBatch": {
                "Paths": {"Items": ["foo.txt", "bar.txt"], "Quantity": 2},
                "CallerReference": "ab",
            },
        },
    )


async def test_create_invalidation_builds_batch_from_paths(
    api: ApiSession,
) -> None:
    await api.assert_params_for_cmd(
        "cloudfront create-invalidation --distribution-id my_id"
        " --paths index.html foo.txt",
        {
            "DistributionId": "my_id",
            "InvalidationBatch": {
                "Paths": {"Items": ["index.html", "foo.txt"], "Quantity": 2},
                "CallerReference": unique_string("cli"),
            },
        },
    )


async def test_get_distribution_config_sends_id(api: ApiSession) -> None:
    await api.assert_params_for_cmd(
        "cloudfront get-distribution-config --id foo", {"Id": "foo"}
    )


async def test_update_distribution_merges_default_root_object(
    api: ApiSession,
) -> None:
    current = {
        **SHORTHAND_DISTRIBUTION_CONFIG,
        "DefaultCacheBehavior": {
            **SHORTHAND_CACHE_BEHAVIOR,
            "ForwardedValues": {
                "QueryString": True,
                "Cookies": {"Forward": "none"},
            },
        },
    }
    result = await api.run(
        UPDATE_DISTRIBUTION + "--default-root-object index.html",
        replies=[{"ETag": "__etag__", "DistributionConfig": current}, {}],
    )
    assert result.operations_with_params == [
        ("GetDistributionConfig", {"Id": "myid"}),
        (
            "UpdateDistribution",
            {
                "DistributionConfig": {
                    **current,
                    "DefaultRootObject": "index.html",
                },
                "Id": "myid",
                "IfMatch": "__etag__",
            },
        ),
    ]


async def test_update_distribution_accepts_distribution_config(
    api: ApiSession,
) -> None:
    await api.assert_params_for_cmd(
        UPDATE_DISTRIBUTION + SHORTHAND_CONFIG,
        {"DistributionConfig": SHORTHAND_DISTRIBUTION_CONFIG, "Id": "myid"},
    )


# A private key only for testing, upstream's TestSign key.
PRIVATE_KEY: Final = (
    "-----BEGIN RSA PRIVATE KEY-----\n"
    "MIIEowIBAAKCAQEAu6o2+Jc8UINw2P/w2l7A1xXu3emQEZQ9diA3bmog8r9Dg+65\n"
    "fZgAqmuNWPqBivv7j3DGnLUdt8uCIr7PYUbK7wDa6n7U3ryOWtO2ZTc3StiJVcqT\n"
    "sokZ0qxGFtDRafjBuydXtcxh52vVTcHqH33nubyyZIzuhTwfmrIOnUXnLwbMrBBP\n"
    "bg/8mlgQooyo1XbrN1eO4XMs+UgQ9Mqc7KRJRinUJ+KYuCnM8f/nN4RjYdjTcghk\n"
    "xCPEHCeSt2luywWyYmfguWCBS2Mu1q0250wKyNazlgiiTJtAuuSeweb4NKPOJL9X\n"
    "hR6Ce6UuU4WYlli8gvQh3FAV3N3C1Rxo20k28QIDAQABAoIBAQCUEkP5dWrzpCJg\n"
    "NeHWizjg/L9SfT1dgXfVQqo6BqckoeElsjDNdifgT6hhcpbQEO52SWeMsiNWp85w\n"
    "l9mNSYxJdIVGzPgtHt27sJyT1DNebOg/tu0+y4qCfcd3rR/u24YQo4RDP5ZoQN82\n"
    "0TBn1LIIDWk8iS6SFdRh/OgnE8bLhNbK9IfZQFEEJrFkArrn/le/ro2mfJkC/imo\n"
    "QvqKmM0dGBXt5SCDSbUQAzKtEcR/4gf/qSjFe2YAwAvSA05WXMH6szdtx6/H/VbK\n"
    "Uck/WwTHvGObQDFEWmICxPK9AWT0qaFNjlUsi3bjQRdIlYYrXe+6nVMB/Jp1awq7\n"
    "tGBqIcWBAoGBAPtXCNuoQhKXqkjJgteQpB+wFav12XRZgpOciYdeviJrgWydpOOu\n"
    "O9wkiRUctUijRJbUuWCJF7SgYGoT2xTTp/COiOReqs7qXLMuuXCZcPKkMRJj5wmo\n"
    "Uc2AwUV/o3+PNz1NFK+2RgciXplac7qugIyuxIvBKuVFTBlCg0+if/0pAoGBAL8k\n"
    "845wKqOeiawwle/o9lKLGPy1T11GrE6l1A5jRuE1WTVM77jRrb0Hmo0mdfHaf5A0\n"
    "EjXGIX/fjcmQzBrEd78eCUsvI2Bgn6xXwhd4TTyWHGZfoQjFqAGkixuLN1oo2h1g\n"
    "bRreFKfAubFP8MC93z23vnH6tdY2VIA4h5ehUFyJAoGAJqxJrKLDJ+E2TmTTQR/8\n"
    "YPPTIdZ+UyzCrrvTXYTydJFeJLxM9suEYmcswJbePgMBNsQckgIGJ8DVlPzhJN88\n"
    "ZANKhPkcByKAiQGTfwPdITiqZE4C6rV/gMNi+bKeEa6TrVcC69Z8B/T94VLNo9fd\n"
    "58esbmSWmRiEkQ5u7f3u+6ECgYA8+6ANCLJB43nPCu07TpsP+LrvHTWF799XdEa0\n"
    "lG3vuiKNA8/TqmoAziU79VJZ6Dkcm9BXga/8aSmGboD/5UDDI+UZLJ/fxtQKmzEc\n"
    "ZdBWjRnge5AYCV+xrnqHPiJZzIDSMIp+sO3sG2vjKzsHc0x/F1lWagOLpWfORLrV\n"
    "4KyP6QKBgAafeSrfK3LM7idiCBuxckLCgFoHa7uXLUNJRS5iIU+bbZLPj2ozu/tk\n"
    "U0jp7sNk1CyMWI36lR3sujkSyH3lPIXVgrXMuGY3PJRGntN8WlWEsw4VUMGRj3h4\n"
    "5rB+y/UOS+nlEwQ6eOS09GByJDEXOXpcwjFcTr/f7V8mi0jH+gY/\n"
    "-----END RSA PRIVATE KEY-----\n"
)
SIGNED_URL: Final = "http://example.com/hi"
CANNED_SIGNATURE: Final = (
    "UiEmtMsInU-gXoa1O7-bTRJmZ~ocphB0ONMxyEHs2r8Y9dwzeB~DkbgzPMX3jbdb"
    "wIwVX3f4VcY4HBLdPSkbF~D6KbUlxPw1ju8mlXeu2C436XxZdrJrrJaiEDaTpKsl"
    "Xpn9ngaCzVfCVPfkC3a0NBWBySi5ezCG2yzb0c-djNgI1wkogwtmtZuOxAoKF1sR"
    "TyFX9ZitUiUIl~65nkJ94s~GGwxzTf1kMi7Wdm~9rFrJpx0O7nJEBy5O578s2UHr"
    "ejtwyedUR5BqXTkgu~A51NcjAN9LErATV7SVBYicoZ76AOfB-TKay7g6-MWCK6-T"
    "-4Q5x6XH4yzII3JpbCmVwA__"
)
CUSTOM_SIGNATURE: Final = (
    "Vw-WG18WJJXim7YSGWS-zW~XmFB9MjCDOvgC~2Gz-1wiMQzCrXzYYbSE7-aF6JGO"
    "Ob5ewArpMqmu2g5mohnqgieZX1NY6IOteDoXYgqaNj1DafHWQD6UJ3IKVfkxISU9"
    "OmFPoG7H~VSPWEzOxdjOqdIPvAU2pW2mJ5oWu2aL62s0VVtLGCAm-DahiSQisl0J"
    "bzpPyG1pofvPbT75qc71r9uiqSAbPjUF5nmLCZazVnFjDkj3zIgMRYa5aV54VDa6"
    "-wEizzmjQ3-m6UMoYgcGHQXEjoFIWTfpZvbZBYkmK9lk3d16cgvaHafTJ-CPegn1"
    "bKxfgNEjSAoPWS0OvBkRmg__"
)
# 2016-01-01T00:00:00Z, the --date-less-than both URLs are signed with.
EXPIRES: Final = 1451606400
CUSTOM_POLICY: Final = {
    "Statement": [
        {
            "Resource": SIGNED_URL,
            "Condition": {
                "DateLessThan": {"AWS:EpochTime": EXPIRES},
                "IpAddress": {"AWS:SourceIp": "12.34.56.78/32"},
            },
        }
    ]
}


def url_b64encode(data: bytes) -> str:
    """CloudFront's URL-safe base64 (botocore's CloudFrontSigner)."""
    return (
        base64.b64encode(data)
        .replace(b"+", b"-")
        .replace(b"=", b"_")
        .replace(b"/", b"~")
        .decode()
    )


@pytest.fixture
def private_key_file(api: ApiSession) -> Path:
    path = api.cwd / "foo.pem"
    path.write_text(PRIVATE_KEY, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("args", "params"),
    [
        pytest.param(
            "",
            {
                "Key-Pair-Id": ["my_id"],
                "Expires": [str(EXPIRES)],
                "Signature": [CANNED_SIGNATURE],
            },
            id="canned-policy",
        ),
        # The policy JSON is compact, its members in the documented order.
        pytest.param(
            " --ip-address 12.34.56.78",
            {
                "Key-Pair-Id": ["my_id"],
                "Policy": [
                    url_b64encode(
                        json.dumps(CUSTOM_POLICY, separators=(",", ":"))
                        .encode()
                    )
                ],
                "Signature": [CUSTOM_SIGNATURE],
            },
            id="custom-policy",
        ),
    ],
)
async def test_sign_prints_signed_url(
    api: ApiSession,
    private_key_file: Path,
    args: str,
    params: dict[str, list[str]],
) -> None:
    result = await api.run(
        [
            *f"cloudfront sign --key-pair-id my_id --url {SIGNED_URL}".split(),
            "--private-key",
            f"file://{private_key_file}",
            *f"--date-less-than 2016-1-1{args}".split(),
        ]
    )
    assert len(result.stdout.splitlines()) == 1
    assert result.stdout.startswith(SIGNED_URL)
    assert parse_qs(urlsplit(result.stdout.strip()).query) == params
    assert result.calls == ()
