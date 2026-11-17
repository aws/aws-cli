"""CloudFormation commands (upstream tests/functional/cloudformation)."""

import json
from typing import Any, Final

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio

CREATE_STACK: Final = (
    "cloudformation create-stack --stack-name test-stack"
    " --template-url http://foo"
)
STACK_PARAMS: Final = {"StackName": "test-stack", "TemplateURL": "http://foo"}


@pytest.mark.parametrize(
    ("args", "params"),
    [
        pytest.param("", STACK_PARAMS, id="basic"),
        pytest.param(
            " --parameters ParameterKey=foo,ParameterValue=bar"
            " ParameterKey=foo2,ParameterValue=bar2",
            {
                **STACK_PARAMS,
                "Parameters": [
                    {"ParameterKey": "foo", "ParameterValue": "bar"},
                    {"ParameterKey": "foo2", "ParameterValue": "bar2"},
                ],
            },
            id="string-params",
        ),
        # A comma in a value is escaped or quoted.
        pytest.param(
            r" --parameters ParameterKey=foo,ParameterValue=one\,two",
            {
                **STACK_PARAMS,
                "Parameters": [
                    {"ParameterKey": "foo", "ParameterValue": "one,two"}
                ],
            },
            id="csv-params-escaping",
        ),
        pytest.param(
            ' --parameters ParameterKey=foo,ParameterValue="one,two"',
            {
                **STACK_PARAMS,
                "Parameters": [
                    {"ParameterKey": "foo", "ParameterValue": "one,two"}
                ],
            },
            id="csv-with-quoting",
        ),
    ],
)
async def test_create_stack_sends_parameters(
    api: ApiSession, args: str, params: dict[str, Any]
) -> None:
    await api.assert_params_for_cmd(CREATE_STACK + args, params)


async def test_create_stack_sends_empty_parameters(api: ApiSession) -> None:
    await api.assert_params_for_cmd(
        "cloudformation create-stack --stack-name test --parameters"
        " --template-url http://foo",
        {"StackName": "test", "TemplateURL": "http://foo", "Parameters": []},
    )


@pytest.mark.parametrize(
    "args",
    [
        pytest.param("", id="single-argument"),
        pytest.param(" --no-paginate", id="no-paginate"),
    ],
)
async def test_describe_stacks_sends_stack_name(
    api: ApiSession, args: str
) -> None:
    await api.assert_params_for_cmd(
        "cloudformation describe-stacks --stack-name test-stack" + args,
        {"StackName": "test-stack"},
    )


async def test_register_type_sends_schema_handler_package(
    api: ApiSession,
) -> None:
    package = "s3://bucket-name/my-organization-resource_name.zip"
    await api.assert_params_for_cmd(
        "cloudformation register-type --type-name test-type-name"
        f" --schema-handler-package {package}",
        {"TypeName": "test-type-name", "SchemaHandlerPackage": package},
    )


async def test_update_stack_sends_stack_policy_during_update_url(
    api: ApiSession,
) -> None:
    await api.assert_params_for_cmd(
        "cloudformation update-stack --stack-name test-stack"
        " --stack-policy-during-update-url http://foo",
        {
            "StackName": "test-stack",
            "StackPolicyDuringUpdateURL": "http://foo",
        },
    )


PARAMETER_TEMPLATE: Final = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Parameters": {
        "Key1": {"Type": "String"},
        "Key2": {"Type": "String"},
    },
}
EMPTY_CHANGESET_REASON: Final = (
    "The submitted information didn't contain changes. "
    "Submit different information to create a change set."
)


def deploy_replies(parameter_keys: list[str]) -> list[dict[str, Any]]:
    """The service's answers to a deploy whose change set is empty.

    Upstream's DescribeStacks fixture gives `Stacks` as a mapping; on the
    wire it is the list of one stack that exists in an OK state, so the
    deploy reads the stack's template summary before it creates an UPDATE
    change set.
    """
    return [
        {"Stacks": [{"StackName": "Stack", "StackStatus": "UPDATE_COMPLETE"}]},
        {
            "Parameters": [
                {"ParameterKey": key, "ParameterType": "String"}
                for key in parameter_keys
            ]
        },
        {"Id": "FakeChangeSetId"},
        # The change set waiter's first poll fails: nothing changed.
        {
            "StackName": "Stack",
            "Status": "FAILED",
            "StatusReason": EMPTY_CHANGESET_REASON,
            "ExecutionStatus": "UNAVAILABLE",
        },
    ]


@pytest.mark.parametrize(
    ("template", "parameter_keys"),
    [
        pytest.param({}, [], id="empty-template"),
        pytest.param(
            PARAMETER_TEMPLATE, ["Key1", "Key2"], id="parameter-template"
        ),
    ],
)
async def test_deploy_fails_on_empty_changeset_when_asked(
    api: ApiSession, template: dict[str, Any], parameter_keys: list[str]
) -> None:
    path = api.cwd / "template.json"
    path.write_text(json.dumps(template), encoding="utf-8")
    result = await api.run(
        [
            "cloudformation",
            "deploy",
            "--template-file",
            str(path),
            "--stack-name",
            "Stack",
            "--fail-on-empty-changeset",
        ],
        replies=deploy_replies(parameter_keys),
        expected_rc=255,
    )
    assert result.operations == [
        "DescribeStacks",
        "GetTemplateSummary",
        "CreateChangeSet",
        "DescribeChangeSet",
    ]
    create = result.calls[2].params
    assert create["ChangeSetType"] == "UPDATE"
    assert create["Parameters"] == [
        {"ParameterKey": key, "UsePreviousValue": True}
        for key in parameter_keys
    ]
    assert "No changes to deploy. Stack Stack is up to date" in result.stderr


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param(
            [
                {
                    "ParameterKey": "Key1",
                    "ParameterValue": "Value1",
                    "RedundantKey": "RedundantValue",
                },
                {"ParameterKey": "Key2", "ParameterValue": "Value2"},
            ],
            id="invalid-cf-like-json-file",
        ),
        pytest.param(
            {"SomeKey": [{"RedundantKey": "RedundantValue"}]},
            id="invalid-json",
        ),
    ],
)
async def test_deploy_rejects_unrecognized_parameter_overrides(
    api: ApiSession, overrides: object
) -> None:
    template = api.cwd / "template.json"
    template.write_text(json.dumps(PARAMETER_TEMPLATE), encoding="utf-8")
    params = api.cwd / "param.json"
    params.write_text(json.dumps(overrides), encoding="utf-8")
    result = await api.run(
        [
            "cloudformation",
            "deploy",
            "--template-file",
            str(template),
            "--stack-name",
            "Stack",
            "--parameter-overrides",
            f"file://{params}",
        ],
        expected_rc=252,
    )
    assert "JSON passed to --parameter-overrides must be" in result.stderr
    assert result.calls == ()
