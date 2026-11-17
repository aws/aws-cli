"""file:// parameter values and their encoding (upstream
tests/functional/test_paramfile.py)."""

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio


async def test_value_without_prefix_is_sent_as_is(api: ApiSession) -> None:
    await api.assert_params_for_cmd(
        "lambda get-function --function-name foobar",
        {"FunctionName": "foobar"},
    )


async def test_file_prefix_sends_file_contents(api: ApiSession) -> None:
    path = api.cwd / "foobar.txt"
    path.write_text("file content", encoding="utf-8")
    await api.assert_params_for_cmd(
        ["lambda", "get-function", "--function-name", f"file://{path}"],
        {"FunctionName": "file content"},
    )


@pytest.mark.parametrize(
    ("encoding", "expected"),
    [
        pytest.param("utf-8", "經理", id="utf8"),
        # The file's UTF-8 bytes read as cp1251.
        pytest.param("cp1251", "з¶“зђ†", id="cp1251"),
    ],
)
async def test_file_prefix_reads_with_env_encoding(
    api: ApiSession, encoding: str, expected: str
) -> None:
    path = api.cwd / "foobar.txt"
    path.write_text("經理", encoding="utf-8")
    api.env["AWS_CLI_FILE_ENCODING"] = encoding
    await api.assert_params_for_cmd(
        ["lambda", "get-function", "--function-name", f"file://{path}"],
        {"FunctionName": expected},
    )
