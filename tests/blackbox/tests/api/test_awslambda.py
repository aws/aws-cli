"""Lambda commands' requests (upstream tests/functional/awslambda)."""

import zipfile
from pathlib import Path
from typing import Any, Final

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio

CREATE_FUNCTION: Final = (
    "lambda create-function --function-name myfunction --runtime myruntime"
    " --role myrole --handler myhandler"
)
PUBLISH_LAYER: Final = "lambda publish-layer-version --layer-name mylayer"
S3_CODE: Final = "S3Bucket=mybucket,S3Key=mykey,S3ObjectVersion=vs"
S3_LOCATION: Final = {
    "S3Bucket": "mybucket",
    "S3Key": "mykey",
    "S3ObjectVersion": "vs",
}
NOT_A_ZIP: Final = " --zip-file filename_instead_of_contents.zip"
FILEB_REQUIRED: Final = "must be a zip file with the fileb:// prefix"


@pytest.fixture
def zip_file(api: ApiSession) -> Path:
    """A zip archive of one small file, as upstream's base class makes."""
    member = api.cwd / "foo"
    member.write_text("mycontents", encoding="utf-8")
    path = api.cwd / "foo.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.write(member, "foo")
    return path


FUNCTION_PARAMS: Final = {
    "FunctionName": "myfunction",
    "Runtime": "myruntime",
    "Role": "myrole",
    "Handler": "myhandler",
}
# Each command's code argument, and whether --zip-file joins it.
CODE_SOURCES: Final = [
    pytest.param(None, True, id="with-file"),
    pytest.param(S3_CODE, False, id="with-s3-location"),
    pytest.param(S3_CODE, True, id="with-s3-location-and-zip-file"),
]


def code_params(
    s3_code: str | None, archive: Path | None
) -> dict[str, Any]:
    """The code structure the arguments build."""
    code: dict[str, Any] = dict(S3_LOCATION) if s3_code else {}
    if archive is not None:
        code["ZipFile"] = archive.read_bytes()
    return code


def code_args(
    option: str, s3_code: str | None, archive: Path | None
) -> list[str]:
    """The code arguments, each path one argument whatever it holds."""
    args = [option, s3_code] if s3_code else []
    if archive is not None:
        args += ["--zip-file", f"fileb://{archive}"]
    return args


@pytest.mark.parametrize(("s3_code", "with_zip"), CODE_SOURCES)
async def test_create_function_merges_zip_file_into_code(
    api: ApiSession, zip_file: Path, s3_code: str | None, with_zip: bool
) -> None:
    archive = zip_file if with_zip else None
    await api.assert_params_for_cmd(
        [*CREATE_FUNCTION.split(), *code_args("--code", s3_code, archive)],
        {**FUNCTION_PARAMS, "Code": code_params(s3_code, archive)},
    )


@pytest.mark.parametrize(("s3_code", "with_zip"), CODE_SOURCES)
async def test_publish_layer_version_merges_zip_file_into_content(
    api: ApiSession, zip_file: Path, s3_code: str | None, with_zip: bool
) -> None:
    archive = zip_file if with_zip else None
    await api.assert_params_for_cmd(
        [
            *PUBLISH_LAYER.split(),
            *code_args("--content", s3_code, archive),
        ],
        {"LayerName": "mylayer", "Content": code_params(s3_code, archive)},
    )


@pytest.mark.parametrize(
    ("command", "message"),
    [
        pytest.param(
            f"{CREATE_FUNCTION} --code {S3_CODE},ZipFile=foo",
            "ZipFile cannot be provided as part of the --code",
            id="function-zip-file-in-code",
        ),
        pytest.param(
            f"{PUBLISH_LAYER} --content {S3_CODE},ZipFile=foo",
            "ZipFile cannot be provided as part of the --content",
            id="layer-zip-file-in-content",
        ),
        pytest.param(
            CREATE_FUNCTION + NOT_A_ZIP,
            FILEB_REQUIRED,
            id="function-invalid-file-contents",
        ),
        pytest.param(
            PUBLISH_LAYER + NOT_A_ZIP,
            FILEB_REQUIRED,
            id="layer-invalid-file-contents",
        ),
        pytest.param(
            "lambda update-function-code --function-name foo" + NOT_A_ZIP,
            FILEB_REQUIRED,
            id="update-code-invalid-file-contents",
        ),
    ],
)
async def test_invalid_code_argument_is_rejected(
    api: ApiSession, command: str, message: str
) -> None:
    result = await api.run(command, expected_rc=252)
    assert message in result.stderr
    assert result.calls == ()


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(CREATE_FUNCTION, id="create-function"),
        pytest.param(PUBLISH_LAYER, id="publish-layer-version"),
    ],
)
async def test_zip_file_with_file_prefix_names_fileb(
    api: ApiSession, zip_file: Path, command: str
) -> None:
    result = await api.run(
        [*command.split(), "--zip-file", f"file://{zip_file}"],
        expected_rc=252,
    )
    assert "fileb://" in result.stderr
    assert result.calls == ()


async def test_update_function_code_reads_fileb_zip_file(
    api: ApiSession, zip_file: Path
) -> None:
    await api.assert_params_for_cmd(
        [
            "lambda",
            "update-function-code",
            "--function-name",
            "myfunction",
            "--zip-file",
            f"fileb://{zip_file}",
        ],
        {"FunctionName": "myfunction", "ZipFile": zip_file.read_bytes()},
    )
