"""`s3 mb`'s requests (upstream tests/functional/s3/test_mb_command.py)."""

from typing import Any, Final

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio

# Upstream answers its us-west-2 CreateBucket rows with the location.
WEST_LOCATION: Final = {"Location": "us-west-2"}


async def test_make_bucket_sends_only_create_bucket(s3api: ApiSession) -> None:
    result = await s3api.run("s3 mb s3://bucket")
    assert result.operations == ["CreateBucket"], result.describe()


@pytest.mark.parametrize(
    ("args", "params", "reply"),
    [
        pytest.param(
            "s3://bucket --region us-west-2",
            {
                "Bucket": "bucket",
                "CreateBucketConfiguration": {
                    "LocationConstraint": "us-west-2"
                },
            },
            WEST_LOCATION,
            id="location-constraint",
        ),
        pytest.param(
            "s3://bucket --region us-east-1",
            {"Bucket": "bucket"},
            None,
            id="no-location-constraint-in-us-east-1",
        ),
        pytest.param(
            "s3://bucket --tags Key1 Value1 --region us-west-2",
            {
                "Bucket": "bucket",
                "CreateBucketConfiguration": {
                    "LocationConstraint": "us-west-2",
                    "Tags": [{"Key": "Key1", "Value": "Value1"}],
                },
            },
            None,
            id="single-tag",
        ),
        pytest.param(
            "s3://bucket --tags Key1 Value1 --region us-east-1",
            {
                "Bucket": "bucket",
                "CreateBucketConfiguration": {
                    "Tags": [{"Key": "Key1", "Value": "Value1"}]
                },
            },
            None,
            id="single-tag-us-east-1",
        ),
        pytest.param(
            "s3://bucket --tags Key1 Value1 --tags Key2 Value2"
            " --region us-west-2",
            {
                "Bucket": "bucket",
                "CreateBucketConfiguration": {
                    "LocationConstraint": "us-west-2",
                    "Tags": [
                        {"Key": "Key1", "Value": "Value1"},
                        {"Key": "Key2", "Value": "Value2"},
                    ],
                },
            },
            None,
            id="multiple-tags",
        ),
        pytest.param(
            "s3://amzn-s3-demo-bucket-111122223333-us-west-2-an"
            " --region us-west-2",
            {
                "Bucket": "amzn-s3-demo-bucket-111122223333-us-west-2-an",
                "BucketNamespace": "account-regional",
                "CreateBucketConfiguration": {
                    "LocationConstraint": "us-west-2"
                },
            },
            WEST_LOCATION,
            id="account-regional-namespace",
        ),
        pytest.param(
            "s3://my-bucket-111122223333-us-east-1-an --region us-east-1",
            {
                "Bucket": "my-bucket-111122223333-us-east-1-an",
                "BucketNamespace": "account-regional",
            },
            None,
            id="account-regional-namespace-us-east-1",
        ),
        pytest.param(
            "s3://xyz-an --region us-east-1",
            {"Bucket": "xyz-an", "BucketNamespace": "account-regional"},
            None,
            id="account-regional-namespace-short-name",
        ),
        pytest.param(
            "s3://my-regular-bucket --region us-east-1",
            {"Bucket": "my-regular-bucket"},
            None,
            id="no-namespace",
        ),
    ],
)
async def test_make_bucket_params(
    s3api: ApiSession,
    args: str,
    params: dict[str, Any],
    reply: dict[str, str] | None,
) -> None:
    await s3api.assert_params_for_cmd(f"s3 mb {args}", params, replies=reply)


@pytest.mark.parametrize(
    ("args", "message"),
    [
        pytest.param("bucket", None, id="invalid-path"),
        pytest.param(
            "s3://bucket--usw2-az1--x-s3/",
            "Cannot use mb command with a directory bucket.",
            id="express-directory-bucket",
        ),
        pytest.param(
            "s3://bucket --tags Key1 Value1 ExtraArg",
            "ParamValidation",
            id="tags-with-three-arguments",
        ),
    ],
)
async def test_make_bucket_rejects_arguments(
    s3api: ApiSession, args: str, message: str | None
) -> None:
    result = await s3api.run(f"s3 mb {args}", expected_rc=252)
    if message is not None:
        assert message in result.stderr, result.describe()
