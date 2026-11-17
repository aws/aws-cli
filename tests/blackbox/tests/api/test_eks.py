"""EKS get-token's token and output (upstream tests/functional/eks)."""

import base64
import json
import re
from typing import Any, Final
from urllib.parse import parse_qs, urlsplit

import pytest

from apihelpers import ApiSession, CommandRun

pytestmark = pytest.mark.asyncio

GET_TOKEN: Final = "eks get-token --cluster-name MyCluster"
ROLE_ARN: Final = "arn:aws:iam::012345678910:role/RoleArn"
ACCESS_KEY: Final = "ABCDEFGHIJKLMNOPQRST"
SECRET_KEY: Final = "TSRQPONMLKJUHGFEDCBA"
SESSION_TOKEN: Final = "TOKENTOKENTOKENTOKEN"
TOKEN_PREFIX: Final = "k8s-aws-v1."
API_GROUP: Final = "client.authentication.k8s.io"
BETA_API: Final = f"{API_GROUP}/v1beta1"


@pytest.fixture
def eks_api(api: ApiSession) -> ApiSession:
    """`api` with upstream's keys, which the token's URL carries."""
    api.env["AWS_ACCESS_KEY_ID"] = ACCESS_KEY
    api.env["AWS_SECRET_ACCESS_KEY"] = SECRET_KEY
    return api


async def get_token(
    api: ApiSession, args: str = "", **options: Any
) -> tuple[CommandRun, Any]:
    """Run get-token; return it and its output's JSON."""
    result = await api.run(f"{GET_TOKEN}{args}", **options)
    return result, json.loads(result.stdout)


def presigned_url(output: dict[str, Any]) -> str:
    """The URL a token encodes: unpadded URL-safe base64 after a prefix."""
    token = output["status"]["token"]
    assert token.startswith(TOKEN_PREFIX)
    encoded = token.removeprefix(TOKEN_PREFIX)
    padding = "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode(encoded + padding).decode()


def assert_presigned_url(
    url: str, host: str, region: str, session_token: str | None = None
) -> None:
    """A GetCallerIdentity URL presigned in `region` for the cluster;
    every part but its time and signature is fixed."""
    parts = urlsplit(url)
    assert (parts.scheme, parts.netloc, parts.path) == ("https", host, "/")
    query = parse_qs(parts.query, keep_blank_values=True)
    [date] = query.pop("X-Amz-Date")
    assert re.fullmatch(r"\d{8}T\d{6}Z", date), url
    [signature] = query.pop("X-Amz-Signature")
    assert re.fullmatch(r"[0-9a-f]{64}", signature), url
    expected = {
        "Action": ["GetCallerIdentity"],
        "Version": ["2011-06-15"],
        "X-Amz-Algorithm": ["AWS4-HMAC-SHA256"],
        "X-Amz-Credential": [
            f"{ACCESS_KEY}/{date[:8]}/{region}/sts/aws4_request"
        ],
        "X-Amz-Expires": ["60"],
        # The cluster's id header is signed.
        "X-Amz-SignedHeaders": ["host;x-k8s-aws-id"],
    }
    if session_token is not None:
        expected["X-Amz-Security-Token"] = [session_token]
    assert query == expected, url


def exec_info(api_version: str) -> str:
    return (
        '{"kind":"ExecCredential",'
        f'"apiVersion":"{API_GROUP}/{api_version}",'
        '"spec":{"interactive":true}}'
    )


@pytest.mark.parametrize(
    ("args", "host", "region"),
    [
        pytest.param("", "sts.us-east-1.amazonaws.com", "us-east-1", id="url"),
        pytest.param(
            " --region us-west-2",
            "sts.us-west-2.amazonaws.com",
            "us-west-2",
            id="url-with-region",
        ),
        pytest.param(
            " --region cn-north-1",
            "sts.cn-north-1.amazonaws.com.cn",
            "cn-north-1",
            id="url-different-partition",
        ),
    ],
)
async def test_url(
    eks_api: ApiSession, args: str, host: str, region: str
) -> None:
    result, output = await get_token(eks_api, args)
    # The URL is presigned locally.
    assert result.calls == ()
    assert_presigned_url(presigned_url(output), host, region)


async def test_url_with_arn(eks_api: ApiSession) -> None:
    credentials = {
        "Credentials": {
            "AccessKeyId": ACCESS_KEY,
            "SecretAccessKey": SECRET_KEY,
            "SessionToken": SESSION_TOKEN,
        }
    }
    result, output = await get_token(
        eks_api, f" --role-arn {ROLE_ARN}", replies=[credentials]
    )
    assert result.operations_with_params == [
        (
            "AssumeRole",
            {"RoleArn": ROLE_ARN, "RoleSessionName": "EKSGetTokenAuth"},
        )
    ]
    # Signed with the role's credentials.
    assert_presigned_url(
        presigned_url(output),
        "sts.us-east-1.amazonaws.com",
        "us-east-1",
        session_token=SESSION_TOKEN,
    )


async def test_query_value(eks_api: ApiSession) -> None:
    _, output = await get_token(eks_api, " --query apiVersion")
    assert output == BETA_API


async def test_token_has_no_padding(eks_api: ApiSession) -> None:
    # Upstream signs 100 tokens to meet every padding. A token's padding
    # depends only on its URL's length mod 3, which the access key's
    # length sets, so three keys meet each padding once.
    residues = set()
    for access_key in (ACCESS_KEY, ACCESS_KEY + "U", ACCESS_KEY + "UV"):
        eks_api.env["AWS_ACCESS_KEY_ID"] = access_key
        _, output = await get_token(eks_api)
        assert "=" not in output["status"]["token"]
        residues.add(len(presigned_url(output)) % 3)
    assert residues == {0, 1, 2}


@pytest.mark.parametrize(
    ("kubernetes_exec_info", "api_version", "stderr"),
    [
        pytest.param(
            exec_info("v1alpha1"),
            f"{API_GROUP}/v1alpha1",
            "Kubeconfig user entry is using deprecated API version"
            f" {API_GROUP}/v1alpha1. Run 'aws eks update-kubeconfig' to"
            " update.\n",
            id="deprecated",
        ),
        pytest.param(
            "{" + exec_info("v1alpha1"),
            BETA_API,
            f"Error parsing KUBERNETES_EXEC_INFO, defaulting to {BETA_API}."
            " This is likely a bug in your Kubernetes client. Please update"
            " your Kubernetes client.\n",
            id="malformed",
        ),
        pytest.param(None, BETA_API, "", id="empty"),
        pytest.param(exec_info("v1"), f"{API_GROUP}/v1", "", id="v1"),
        pytest.param(exec_info("v1beta1"), BETA_API, "", id="v1beta1"),
        pytest.param(
            exec_info("v2"),
            BETA_API,
            "Unrecognized API version in KUBERNETES_EXEC_INFO, defaulting"
            f" to {BETA_API}. This is likely due to an outdated AWS CLI."
            " Please update your AWS CLI.\n",
            id="unknown",
        ),
    ],
)
async def test_api_version_discovery(
    eks_api: ApiSession,
    kubernetes_exec_info: str | None,
    api_version: str,
    stderr: str,
) -> None:
    if kubernetes_exec_info is not None:
        eks_api.env["KUBERNETES_EXEC_INFO"] = kubernetes_exec_info
    result, output = await get_token(eks_api)
    assert output["apiVersion"] == api_version
    assert result.stderr == stderr
