"""--cli-input-json and --cli-input-yaml (upstream
tests/functional/test_cliinput.py)."""

from typing import Any, Final

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio

INPUT_JSON: Final = '{"Bucket": "bucket", "Key": "key"}'
INPUT_YAML: Final = "Bucket: test-bucket\nEncodingType: url"
YAML_PARAMS: Final = {"Bucket": "test-bucket", "EncodingType": "url"}
# Stands for the path of the input file a test writes.
INPUT_FILE: Final = "<input-file>"


@pytest.mark.parametrize(
    ("args", "params"),
    [
        pytest.param(
            ["--cli-input-json", f"file://{INPUT_FILE}"],
            {"Bucket": "bucket", "Key": "key"},
            id="from-file",
        ),
        pytest.param(
            ["--key", "bar", "--cli-input-json", f"file://{INPUT_FILE}"],
            {"Bucket": "bucket", "Key": "bar"},
            id="option-overrides-input",
        ),
        pytest.param(
            ["--cli-input-json", '{"Bucket":"bucket","Key":"key"}'],
            {"Bucket": "bucket", "Key": "key"},
            id="not-from-file",
        ),
    ],
)
async def test_cli_input_json_supplies_params(
    api: ApiSession, args: list[str], params: dict[str, Any]
) -> None:
    input_file = api.cwd / "foo.json"
    input_file.write_text(INPUT_JSON, encoding="utf-8")
    argv = [arg.replace(INPUT_FILE, str(input_file)) for arg in args]
    run = await api.assert_params_for_cmd(
        ["s3api", "head-object", *argv], params
    )
    assert run.operations == ["HeadObject"]


@pytest.mark.parametrize(
    ("input_json", "message"),
    [
        pytest.param('{"Key":"foo"}', "Missing", id="missing-required"),
        pytest.param(
            '{"Bucket":"bucket","Key":"key","Foo":"bar"}',
            "Unknown",
            id="extra-unknown-args",
        ),
    ],
)
async def test_cli_input_json_is_validated(
    api: ApiSession, input_json: str, message: str
) -> None:
    run = await api.assert_params_for_cmd(
        ["s3api", "head-object", "--cli-input-json", input_json],
        expected_rc=252,
        stderr_contains=message,
    )
    assert run.calls == ()


@pytest.mark.parametrize(
    "input_yaml",
    [
        pytest.param(INPUT_YAML, id="inline"),
        pytest.param(f"file://{INPUT_FILE}", id="from-file"),
        pytest.param(
            "Bucket: test-bucket # Some comment\nEncodingType: url",
            id="ignores-comments",
        ),
    ],
)
async def test_cli_input_yaml_supplies_params(
    api: ApiSession, input_yaml: str
) -> None:
    input_file = api.cwd / "input.yml"
    input_file.write_text(INPUT_YAML, encoding="utf-8")
    run = await api.assert_params_for_cmd(
        [
            "s3api",
            "list-objects-v2",
            "--cli-input-yaml",
            input_yaml.replace(INPUT_FILE, str(input_file)),
        ],
        YAML_PARAMS,
    )
    assert run.operations == ["ListObjectsV2"]


@pytest.mark.parametrize(
    "input_yaml",
    [
        pytest.param("Bucket: test-bucket\nFoo: bar", id="unknown-params"),
        pytest.param("EncodingType: url", id="required-params-missing"),
    ],
)
async def test_cli_input_yaml_is_validated(
    api: ApiSession, input_yaml: str
) -> None:
    run = await api.run(
        ["s3api", "list-objects-v2", "--cli-input-yaml", input_yaml],
        expected_rc=252,
    )
    assert run.calls == ()


async def test_cli_input_yaml_and_json_are_exclusive(api: ApiSession) -> None:
    run = await api.assert_params_for_cmd(
        [
            "s3api",
            "list-objects-v2",
            "--cli-input-yaml",
            "Bucket: test-bucket # Some comment\nEncodingType: url",
            "--cli-input-json",
            '{"Bucket":"bucket","Key":"key"}',
        ],
        expected_rc=252,
        stderr_contains="Only one --cli-input- parameter may be specified.",
    )
    assert run.calls == ()
