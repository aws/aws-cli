"""The s3 commands' refusal of Object Lambda access points (upstream
tests/functional/s3/test_s3_object_lambda.py).

Native hands these operands to the Python CLI, so each command runs once,
in upstream's environment, rather than on both transfer clients.
"""

from typing import Final

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio

ARN: Final = "arn:aws:s3-object-lambda:us-west-2:123456789012:accesspoint"


@pytest.mark.parametrize(
    "operand",
    [
        pytest.param(f"{ARN}:my-accesspoint", id="colon"),
        pytest.param(f"{ARN}/my-accesspoint", id="slash"),
        pytest.param(f"{ARN}:my-accesspoint/my-key", id="colon-with-key"),
        pytest.param(f"{ARN}/my-accesspoint/my-key", id="slash-with-key"),
    ],
)
@pytest.mark.parametrize(
    "command",
    [
        pytest.param("s3 ls s3://{operand}", id="ls"),
        pytest.param("s3 cp s3://{operand} .", id="cp"),
        pytest.param("s3 mv s3://{operand} .", id="mv"),
        pytest.param("s3 sync s3://{operand} .", id="sync"),
        pytest.param("s3 rm s3://{operand}", id="rm"),
        pytest.param("s3 mb s3://{operand}", id="mb"),
        pytest.param("s3 presign s3://{operand}", id="presign"),
        pytest.param("s3 rb s3://{operand}", id="rb"),
        pytest.param("s3 website s3://{operand}", id="website"),
    ],
)
async def test_s3_commands_refuse_object_lambda_arn(
    s3api: ApiSession, command: str, operand: str
) -> None:
    result = await s3api.run(
        command.format(operand=operand), expected_rc=252
    )
    assert "s3 commands do not support" in result.stderr, result.describe()
