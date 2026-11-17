"""QuickSight asset bundle import's source body (upstream
tests/functional/quicksight)."""

from typing import Final

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio

IMPORT_JOB: Final = (
    "quicksight start-asset-bundle-import-job --aws-account-id 123456789012"
    " --asset-bundle-import-job-id import-job-1"
)


async def test_can_provide_source_body_as_top_level_param(
    api: ApiSession,
) -> None:
    source = api.cwd / "foo"
    source.write_bytes(b"mycontents")
    await api.assert_params_for_cmd(
        [
            *IMPORT_JOB.split(),
            "--asset-bundle-import-source-bytes",
            f"fileb://{source}",
        ],
        {
            "AwsAccountId": "123456789012",
            "AssetBundleImportJobId": "import-job-1",
            "AssetBundleImportSource": {"Body": b"mycontents"},
        },
    )


async def test_can_provide_source_body_as_nested_param(
    api: ApiSession,
) -> None:
    # The nested Body is a blob given in base64: "hello world".
    await api.assert_params_for_cmd(
        f"{IMPORT_JOB} --asset-bundle-import-source Body=aGVsbG8gd29ybGQ=",
        {
            "AwsAccountId": "123456789012",
            "AssetBundleImportJobId": "import-job-1",
            "AssetBundleImportSource": {"Body": b"hello world"},
        },
    )
