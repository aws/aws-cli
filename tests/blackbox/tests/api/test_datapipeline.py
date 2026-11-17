"""Data Pipeline commands (upstream tests/functional/datapipeline)."""

from typing import Any

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio


async def test_get_pipeline_definition_renames_version_argument(
    api: ApiSession,
) -> None:
    # --pipeline-version keeps clear of the global --version.
    await api.assert_params_for_cmd(
        "datapipeline get-pipeline-definition --pipeline-id foo"
        " --pipeline-version latest",
        {"pipelineId": "foo", "version": "latest"},
    )


async def test_query_objects_renames_query_argument(api: ApiSession) -> None:
    # --objects-query keeps clear of the global --query.
    await api.assert_params_for_cmd(
        "datapipeline query-objects --pipeline-id foo --sphere INSTANCE"
        ' --objects-query {"selectors":[{"fieldName":"@status",'
        '"operator":{"type":"EQ","values":["RUNNING"]}}]}',
        {
            "pipelineId": "foo",
            "query": {
                "selectors": [
                    {
                        "fieldName": "@status",
                        "operator": {"type": "EQ", "values": ["RUNNING"]},
                    }
                ]
            },
            "sphere": "INSTANCE",
        },
    )


def pipeline_objects(object_ids: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "id": object_id,
            "name": object_id,
            "fields": [{"key": "@componentParent", "stringValue": object_id}],
        }
        for object_id in object_ids
    ]


async def test_list_runs_pages_more_than_one_hundred_runs(
    api: ApiSession,
) -> None:
    start_date = "2017-10-22T00:37:21"
    end_date = "2017-10-26T00:37:21"
    object_ids = [f"object-id-{index}" for index in range(150)]
    objects = pipeline_objects(object_ids)
    replies = [
        {"ids": object_ids[:100], "hasMoreResults": True, "marker": "marker"},
        {"ids": object_ids[100:], "hasMoreResults": False},
        {"pipelineObjects": objects[:100]},
        {"pipelineObjects": objects[100:]},
    ]
    result = await api.run(
        "datapipeline list-runs --pipeline-id pipeline-id"
        f" --start-interval {start_date},{end_date}",
        replies=replies,
    )
    query = {
        "selectors": [
            {
                "fieldName": "@actualStartTime",
                "operator": {
                    "type": "BETWEEN",
                    "values": [start_date, end_date],
                },
            }
        ]
    }
    assert result.operations_with_params == [
        (
            "QueryObjects",
            {
                "pipelineId": "pipeline-id",
                "query": query,
                "sphere": "INSTANCE",
            },
        ),
        (
            "QueryObjects",
            {
                "pipelineId": "pipeline-id",
                "marker": "marker",
                "query": query,
                "sphere": "INSTANCE",
            },
        ),
        (
            "DescribeObjects",
            {"objectIds": object_ids[:100], "pipelineId": "pipeline-id"},
        ),
        (
            "DescribeObjects",
            {"objectIds": object_ids[100:], "pipelineId": "pipeline-id"},
        ),
    ]
