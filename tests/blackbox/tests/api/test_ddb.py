"""DynamoDB `ddb` commands (upstream tests/functional/ddb)."""

import json
from typing import Any, Final

import pytest
from ruamel.yaml import YAML

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio

PUT_ITEM: Final = {
    "TableName": "mytable",
    "ReturnConsumedCapacity": "NONE",
    "Item": {"foo": {"S": "bar"}},
}
SCAN: Final = {
    "TableName": "mytable",
    "ReturnConsumedCapacity": "NONE",
    "ConsistentRead": True,
}
SELECT_REPLY: Final = {
    "Count": 1,
    "Items": [{"foo": {"S": "spam"}}],
    "ScannedCount": 1,
}
# Two pages of one item each.
PAGES: Final = [
    {
        "Count": 1,
        "Items": [{"foo": {"N": "1"}}],
        "ScannedCount": 1,
        "LastEvaluatedKey": {"foo": {"N": "1"}},
    },
    {"Count": 1, "Items": [{"foo": {"N": "2"}}], "ScannedCount": 1},
]
# The --starting-token that resumes after the first page.
FIRST_PAGE_TOKEN: Final = (
    "eyJFeGNsdXNpdmVTdGFydEtleSI6IHsiZm9vIjogeyJOIjogIjEifX19"
)


def assert_yaml_output(output: str, expected: object) -> None:
    """The output is YAML, not JSON, and loads to `expected`."""
    with pytest.raises(ValueError):
        json.loads(output)
    assert YAML(typ="safe", pure=True).load(output) == expected


async def test_ddb_without_subcommand_prints_usage(api: ApiSession) -> None:
    result = await api.run("ddb", expected_rc=252)
    assert (
        "usage: aws [options] ddb <subcommand> [parameters]\n"
        "aws: [ERROR]: too few arguments"
    ) in result.stderr


@pytest.mark.parametrize(
    ("items", "item"),
    [
        pytest.param("{foo: bar}", {"foo": {"S": "bar"}}, id="simple"),
        pytest.param(
            '{foo: !!binary "4pyT"}',
            {"foo": {"B": b"\xe2\x9c\x93"}},
            id="bytes",
        ),
        pytest.param("{foo: 1}", {"foo": {"N": "1"}}, id="int"),
        pytest.param("{foo: 1.1}", {"foo": {"N": "1.1"}}, id="float"),
    ],
)
async def test_put_sends_put_item(
    api: ApiSession, items: str, item: dict[str, Any]
) -> None:
    result = await api.assert_params_for_cmd(
        ["ddb", "put", "mytable", items], {**PUT_ITEM, "Item": item}
    )
    assert result.operations == ["PutItem"]


async def test_put_loads_items_from_file(api: ApiSession) -> None:
    path = api.cwd / "items.yml"
    path.write_text("{foo: bar}\n", encoding="utf-8")
    await api.assert_params_for_cmd(
        ["ddb", "put", "mytable", f"file://{path}"], PUT_ITEM
    )


async def test_put_sends_condition(api: ApiSession) -> None:
    await api.assert_params_for_cmd(
        ["ddb", "put", "mytable", "{foo: bar}"]
        + ["--condition", "attribute_exists(foo)"],
        {
            **PUT_ITEM,
            "ConditionExpression": "attribute_exists(#n0)",
            "ExpressionAttributeNames": {"#n0": "foo"},
        },
    )


async def test_put_list_sends_batch_write(api: ApiSession) -> None:
    put = {"PutRequest": {"Item": {"foo": {"S": "bar"}}}}
    result = await api.assert_params_for_cmd(
        ["ddb", "put", "mytable", "[{foo: bar}, {foo: bar}]"],
        {
            "ReturnConsumedCapacity": "NONE",
            "RequestItems": {"mytable": [put, put]},
        },
    )
    assert result.operations == ["BatchWriteItem"]


async def test_put_list_rejects_condition(api: ApiSession) -> None:
    result = await api.assert_params_for_cmd(
        ["ddb", "put", "mytable", "[{foo: bar}, {foo: bar}]"]
        + ["--condition", "attribute_exists(foo)"],
        expected_rc=252,
        stderr_contains="--condition is not supported",
    )
    assert result.calls == ()


def batch_sizes(calls: list[dict[str, Any]]) -> list[int]:
    return [len(params["RequestItems"]["mytable"]) for params in calls]


FORTY_ITEMS: Final = "[" + ", ".join(["{foo: bar}"] * 40) + "]"


async def test_put_batches_twenty_five_items_a_request(
    api: ApiSession,
) -> None:
    result = await api.run(["ddb", "put", "mytable", FORTY_ITEMS])
    assert result.operations == ["BatchWriteItem", "BatchWriteItem"]
    params = [call.params for call in result.calls]
    assert batch_sizes(params) == [25, 15]
    assert [p.get("ReturnConsumedCapacity") for p in params] == [
        "NONE",
        "NONE",
    ]


async def test_put_resends_unprocessed_items(api: ApiSession) -> None:
    unprocessed = {
        "UnprocessedItems": {
            "mytable": [{"PutRequest": {"Item": {"foo": {"S": "bar"}}}}]
        }
    }
    result = await api.run(
        ["ddb", "put", "mytable", FORTY_ITEMS],
        replies=[unprocessed, unprocessed, {}],
    )
    assert result.operations == ["BatchWriteItem"] * 3
    assert batch_sizes([call.params for call in result.calls]) == [25, 16, 1]


async def test_select_with_attributes_count(api: ApiSession) -> None:
    reply = {"Count": 1, "ScannedCount": 1}
    result = await api.assert_params_for_cmd(
        ["ddb", "select", "mytable", "--attributes", "COUNT"],
        {**SCAN, "Select": "COUNT"},
        replies=reply,
    )
    assert_yaml_output(result.stdout, reply)


async def test_select_returns_bytes(api: ApiSession) -> None:
    result = await api.run(
        ["ddb", "select", "mytable"],
        replies={
            "Count": 1,
            "Items": [{"foo": {"B": b"\xe2\x9c\x93"}}],
            "ScannedCount": 1,
        },
    )
    assert_yaml_output(
        result.stdout,
        {"Count": 1, "Items": [{"foo": b"\xe2\x9c\x93"}], "ScannedCount": 1},
    )


async def test_select_omits_null_consumed_capacity(api: ApiSession) -> None:
    # The wire carries the null upstream's fixture gives.
    result = await api.run(
        ["ddb", "select", "mytable"],
        replies={**SELECT_REPLY, "ConsumedCapacity": None},
    )
    assert_yaml_output(
        result.stdout,
        {"Count": 1, "Items": [{"foo": "spam"}], "ScannedCount": 1},
    )


async def test_select_with_multiple_expressions(api: ApiSession) -> None:
    await api.assert_params_for_cmd(
        ["ddb", "select", "laptops", "--projection", "name, price"]
        + ["--filter", "price < 3000", "--key-condition", 'name = "macbook"'],
        {
            "TableName": "laptops",
            "ReturnConsumedCapacity": "NONE",
            "ConsistentRead": True,
            "ProjectionExpression": "#n0, #n1",
            "FilterExpression": "#n2 < :n3",
            "KeyConditionExpression": "#n4 = :n5",
            "ExpressionAttributeNames": {
                "#n0": "name",
                "#n1": "price",
                "#n2": "price",
                "#n4": "name",
            },
            "ExpressionAttributeValues": {
                ":n3": {"N": "3000"},
                ":n5": {"S": "macbook"},
            },
        },
        replies={
            "Count": 1,
            "Items": [{"name": {"S": "macbook"}, "price": {"N": "2000"}}],
            "ScannedCount": 1,
        },
    )


async def test_select_projects_complex_identifier(api: ApiSession) -> None:
    await api.assert_params_for_cmd(
        ["ddb", "select", "recipes"]
        + ["--projection", "name, ingredients[8].name"],
        {
            "TableName": "recipes",
            "ReturnConsumedCapacity": "NONE",
            "ConsistentRead": True,
            "ProjectionExpression": "#n0, #n1[8].#n2",
            "ExpressionAttributeNames": {
                "#n0": "name",
                "#n1": "ingredients",
                "#n2": "name",
            },
        },
        replies={
            "Count": 1,
            "Items": [
                {
                    "name": {"S": "spam n eggs"},
                    "ingredients": {"L": [{"M": {"name": {"S": "spam"}}}]},
                }
            ],
        },
    )


@pytest.mark.parametrize("output", ["json", "table", "text", "yaml-stream"])
async def test_select_rejects_unsupported_output(
    api: ApiSession, output: str
) -> None:
    result = await api.assert_params_for_cmd(
        f"ddb select mytable --output {output}",
        expected_rc=252,
        stderr_contains=(
            f"{output} output format is not supported for ddb commands"
        ),
    )
    assert result.calls == ()


async def test_select_parse_error_exits_252(api: ApiSession) -> None:
    result = await api.run(
        "ddb select mytable --filter a=?!f", expected_rc=252
    )
    assert result.calls == ()


async def test_select_follows_pages(api: ApiSession) -> None:
    result = await api.run(["ddb", "select", "mytable"], replies=PAGES)
    assert_yaml_output(
        result.stdout,
        {"Count": 2, "Items": [{"foo": 1}, {"foo": 2}], "ScannedCount": 2},
    )


async def test_select_no_paginate_prints_first_page(api: ApiSession) -> None:
    result = await api.run(
        ["ddb", "select", "mytable", "--no-paginate"], replies=PAGES
    )
    assert_yaml_output(
        result.stdout,
        {
            "Count": 1,
            "Items": [{"foo": 1}],
            "ScannedCount": 1,
            "LastEvaluatedKey": {"foo": 1},
        },
    )


async def test_select_no_paginate_rejects_paging_params(
    api: ApiSession,
) -> None:
    result = await api.run(
        ["ddb", "select", "mytable", "--no-paginate", "--max-items", "1"],
        replies=PAGES,
        expected_rc=252,
    )
    assert "Cannot specify --no-paginate along with " in result.stderr
    assert result.calls == ()


async def test_select_max_items_prints_next_token(api: ApiSession) -> None:
    result = await api.run(
        ["ddb", "select", "mytable", "--max-items", "1"], replies=PAGES
    )
    assert_yaml_output(
        result.stdout,
        {
            "Count": 1,
            "Items": [{"foo": 1}],
            "ScannedCount": 1,
            "NextToken": FIRST_PAGE_TOKEN,
        },
    )


async def test_select_page_size_sets_limit(api: ApiSession) -> None:
    result = await api.run(
        ["ddb", "select", "mytable", "--page-size", "1"], replies=PAGES
    )
    assert result.calls[1].params == {
        **SCAN,
        "ExclusiveStartKey": {"foo": {"N": "1"}},
        "Limit": 1,
    }
    assert_yaml_output(
        result.stdout,
        {"Count": 2, "Items": [{"foo": 1}, {"foo": 2}], "ScannedCount": 2},
    )


async def test_select_starting_token_resumes(api: ApiSession) -> None:
    result = await api.assert_params_for_cmd(
        ["ddb", "select", "mytable", "--starting-token", FIRST_PAGE_TOKEN],
        {**SCAN, "ExclusiveStartKey": {"foo": {"N": "1"}}},
        replies=[PAGES[1]],
    )
    assert_yaml_output(
        result.stdout,
        {"Count": 1, "Items": [{"foo": 2}], "ScannedCount": 1},
    )
