"""RDS commands' requests (upstream tests/functional/rds)."""

from typing import Any

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio


async def test_describe_db_log_files(api: ApiSession) -> None:
    await api.assert_params_for_cmd(
        "rds describe-db-log-files --file-last-written 10"
        " --db-instance-identifier foo",
        {"DBInstanceIdentifier": "foo", "FileLastWritten": 10},
    )


# modify-option-group is split into add-option-to-option-group and
# remove-option-from-option-group, each with its own --options.
@pytest.mark.parametrize(
    ("command", "options", "params"),
    [
        pytest.param(
            "add-option-to-option-group",
            '{"OptionName":"TDE"}',
            {"OptionsToInclude": [{"OptionName": "TDE"}]},
            id="add-option",
        ),
        pytest.param(
            "remove-option-from-option-group",
            "TDE",
            {"OptionsToRemove": ["TDE"]},
            id="remove-options",
        ),
    ],
)
async def test_option_group_options(
    api: ApiSession, command: str, options: str, params: dict[str, Any]
) -> None:
    await api.assert_params_for_cmd(
        f"rds {command} --option-group-name myoptiongroup2"
        f" --options {options}",
        {**params, "OptionGroupName": "myoptiongroup2"},
    )


@pytest.mark.parametrize(
    ("command", "option", "value"),
    [
        pytest.param(
            "add-option-to-option-group",
            "--options-to-remove",
            "foo",
            id="option-to-remove-is-not-allowed",
        ),
        pytest.param(
            "remove-option-from-option-group",
            "--options-to-include",
            '{"OptionName":"TDE"}',
            id="option-to-add-is-not-allowed",
        ),
    ],
)
async def test_option_group_rejects_other_commands_option(
    api: ApiSession, command: str, option: str, value: str
) -> None:
    result = await api.assert_params_for_cmd(
        f"rds {command} --option-group-name myoptiongroup2 {option} {value}",
        expected_rc=252,
        stderr_contains=f"Unknown options: {option}",
    )
    assert result.calls == ()
