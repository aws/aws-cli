"""Service Catalog's generate commands (upstream
tests/functional/servicecatalog)."""

import base64
import uuid
from dataclasses import dataclass, replace
from typing import Any, Final

import awscrt.checksums
import pytest

from apihelpers import ApiSession, CommandRun

pytestmark = pytest.mark.asyncio

TEMPLATE_NAME: Final = "development-environment.template"
# Stands in for upstream's sample template, which the command uploads
# unchanged. It sits in the command's working directory, so its name is the
# --file-path upstream gives as an absolute path.
TEMPLATE: Final = b'{\n  "AWSTemplateFormatVersion" : "2010-09-09"\n}\n'
# botocore adds the default checksum to the upload.
TEMPLATE_CRC64NVME: Final = base64.b64encode(
    awscrt.checksums.crc64nvme(TEMPLATE).to_bytes(8, "big")
).decode()
BUCKET: Final = "bucket_name"
TEMPLATE_URL: Final = f"https://s3.amazonaws.com/{BUCKET}/{TEMPLATE_NAME}"
CFN_TYPE: Final = "CLOUD_FORMATION_TEMPLATE"
TAGS: Final = (
    "Key=key1,Value=value1",
    "Key=key2,Value=value2",
    "Key=key3,Value=value3",
)
PRODUCT_ID: Final = "prod-1234567890abc"


def options(*pairs: tuple[str, str | None]) -> list[str]:
    """Each option whose value is not None, followed by its value."""
    argv: list[str] = []
    for option, value in pairs:
        if value is not None:
            argv += [option, value]
    return argv


@dataclass(frozen=True)
class ProductArgs:
    """`generate product`'s arguments, upstream's `init_params`; None
    leaves an option out."""

    file_path: str | None = TEMPLATE_NAME
    bucket_name: str | None = BUCKET
    product_name: str | None = "prod_name"
    product_owner: str | None = "prod_owner"
    product_type: str | None = CFN_TYPE
    pa_name: str | None = "prov_art_name"
    pa_description: str | None = "prov_art_desc"
    pa_type: str | None = CFN_TYPE
    support_description: str = "support_desc"

    def argv(self) -> list[str]:
        return [
            "servicecatalog",
            "generate",
            "product",
            *options(
                ("--file-path", self.file_path),
                ("--bucket-name", self.bucket_name),
                ("--product-name", self.product_name),
            ),
            "--tags",
            *TAGS,
            *options(
                ("--product-owner", self.product_owner),
                ("--product-type", self.product_type),
                ("--provisioning-artifact-name", self.pa_name),
                ("--provisioning-artifact-description", self.pa_description),
                ("--provisioning-artifact-type", self.pa_type),
                ("--product-description", "prod_desc"),
                ("--product-distributor", "prod_dist"),
                ("--support-description", self.support_description),
                ("--support-email", "support_email"),
            ),
        ]

    def create_product_params(self) -> dict[str, Any]:
        return {
            "Description": "prod_desc",
            "Distributor": "prod_dist",
            "Name": self.product_name,
            "Owner": self.product_owner,
            "ProductType": self.product_type,
            "ProvisioningArtifactParameters": {
                "Description": self.pa_description,
                "Info": {"LoadTemplateFromURL": TEMPLATE_URL},
                "Name": self.pa_name,
                "Type": self.pa_type,
            },
            "SupportDescription": self.support_description,
            "SupportEmail": "support_email",
            "Tags": [
                {"Value": "value1", "Key": "key1"},
                {"Value": "value2", "Key": "key2"},
                {"Value": "value3", "Key": "key3"},
            ],
        }


@dataclass(frozen=True)
class ArtifactArgs:
    """`generate provisioning-artifact`'s arguments, upstream's
    `init_params`; None leaves an option out."""

    file_path: str | None = TEMPLATE_NAME
    bucket_name: str | None = BUCKET
    pa_name: str | None = "prov_art_name"
    pa_description: str | None = "prov_art_desc"
    pa_type: str | None = CFN_TYPE

    def argv(self) -> list[str]:
        return [
            "servicecatalog",
            "generate",
            "provisioning-artifact",
            *options(
                ("--file-path", self.file_path),
                ("--bucket-name", self.bucket_name),
                ("--provisioning-artifact-name", self.pa_name),
                ("--provisioning-artifact-description", self.pa_description),
                ("--provisioning-artifact-type", self.pa_type),
                ("--product-id", PRODUCT_ID),
            ),
        ]

    def create_artifact_params(self) -> dict[str, Any]:
        return {
            "Parameters": {
                "Description": self.pa_description,
                "Info": {"LoadTemplateFromURL": TEMPLATE_URL},
                "Name": self.pa_name,
                "Type": self.pa_type,
            },
            "ProductId": PRODUCT_ID,
        }


@pytest.fixture(autouse=True)
def template(api: ApiSession) -> None:
    (api.cwd / TEMPLATE_NAME).write_bytes(TEMPLATE)


def assert_uploaded_then_created(
    run: CommandRun, operation: str, params: dict[str, Any]
) -> None:
    """The template went to the bucket, then `operation` was called with
    `params` and a generated idempotency token."""
    assert run.operations == ["PutObject", operation], run.describe()
    upload = run.calls[0].params
    assert upload == {
        "Bucket": BUCKET,
        "Key": TEMPLATE_NAME,
        "Body": TEMPLATE,
        "ServerSideEncryption": "AES256",
        "ChecksumAlgorithm": "CRC64NVME",
        "ChecksumCRC64NVME": TEMPLATE_CRC64NVME,
    }, run.describe()
    created = dict(run.calls[1].params)
    token = created.pop("IdempotencyToken")
    assert uuid.UUID(token).version == 4, token
    assert created == params, run.describe()


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(ProductArgs(), id="ascii"),
        pytest.param(
            ProductArgs(
                product_name="\u05d1\u05e8\u05d9\u05e6\u05e7\u05dc\u05d4",
                support_description="\u00fd\u00a9\u0194\u0292",
            ),
            id="unicode",
        ),
    ],
)
async def test_generate_product_uploads_template_and_creates_product(
    api: ApiSession, args: ProductArgs
) -> None:
    run = await api.run(args.argv())
    assert_uploaded_then_created(
        run, "CreateProduct", args.create_product_params()
    )


@pytest.mark.parametrize(
    ("args", "rc", "message"),
    [
        pytest.param(
            ProductArgs(file_path="invalid/template/file"),
            255,
            "cannot be found",
            id="invalid-path",
        ),
        pytest.param(
            ProductArgs(product_type="invalid-product-type"),
            252,
            "--product-type: Found invalid choice",
            id="invalid-product-type",
        ),
        pytest.param(
            ProductArgs(pa_type="invalid_provisioning type"),
            252,
            "--provisioning-artifact-type: Found invalid choice",
            id="invalid-provisioning-artifact-type",
        ),
        *(
            pytest.param(
                replace(ProductArgs(), **{field: None}),
                252,
                option,
                id=f"missing-{option.removeprefix('--')}",
            )
            for field, option in [
                ("file_path", "--file-path"),
                ("bucket_name", "--bucket-name"),
                ("product_name", "--product-name"),
                ("product_owner", "--product-owner"),
                ("product_type", "--product-type"),
                ("pa_name", "--provisioning-artifact-name"),
                ("pa_description", "--provisioning-artifact-description"),
                ("pa_type", "--provisioning-artifact-type"),
            ]
        ),
    ],
)
async def test_generate_product_rejects_bad_args(
    api: ApiSession, args: ProductArgs, rc: int, message: str
) -> None:
    run = await api.assert_params_for_cmd(
        args.argv(),
        expected_rc=rc,
        stderr_contains=message,
    )
    assert run.calls == ()


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(ArtifactArgs(), id="ascii"),
        pytest.param(
            ArtifactArgs(
                pa_name="\u05d1\u05e8\u05d9\u05e6\u05e7",
                pa_description="\u00fd\u00a9\u0194\u0292",
            ),
            id="unicode",
        ),
    ],
)
async def test_generate_provisioning_artifact_uploads_template(
    api: ApiSession, args: ArtifactArgs
) -> None:
    run = await api.run(args.argv())
    assert_uploaded_then_created(
        run, "CreateProvisioningArtifact", args.create_artifact_params()
    )


@pytest.mark.parametrize(
    ("args", "rc", "message"),
    [
        pytest.param(
            ArtifactArgs(file_path="invalid/template/file"),
            255,
            "cannot be found",
            id="invalid-path",
        ),
        pytest.param(
            ArtifactArgs(pa_type="invalid_provisioning type"),
            252,
            "--provisioning-artifact-type: Found invalid choice",
            id="invalid-provisioning-artifact-type",
        ),
        *(
            pytest.param(
                replace(ArtifactArgs(), **{field: None}),
                252,
                option,
                id=f"missing-{option.removeprefix('--')}",
            )
            for field, option in [
                ("file_path", "--file-path"),
                ("bucket_name", "--bucket-name"),
                ("pa_name", "--provisioning-artifact-name"),
                ("pa_description", "--provisioning-artifact-description"),
                ("pa_type", "--provisioning-artifact-type"),
            ]
        ),
    ],
)
async def test_generate_provisioning_artifact_rejects_bad_args(
    api: ApiSession, args: ArtifactArgs, rc: int, message: str
) -> None:
    run = await api.assert_params_for_cmd(
        args.argv(),
        expected_rc=rc,
        stderr_contains=message,
    )
    assert run.calls == ()
