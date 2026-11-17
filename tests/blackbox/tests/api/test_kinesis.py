"""Kinesis list-streams' pagination (upstream tests/functional/kinesis)."""

import json

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio


async def test_exclusive_start_stream_name_disables_auto_pagination(
    api: ApiSession,
) -> None:
    page = {
        "StreamNames": ["stream-1", "stream-2"],
        "StreamSummaries": [
            {"StreamName": "stream-1"},
            {"StreamName": "stream-2"},
        ],
        "HasMoreStreams": True,
        "NextToken": "token",
    }
    # One reply: a second page request would fail the test.
    result = await api.assert_params_for_cmd(
        "kinesis list-streams --exclusive-start-stream-name stream-1",
        {"ExclusiveStartStreamName": "stream-1"},
        replies=[page],
    )
    # The page is printed as it came, its NextToken and HasMoreStreams
    # included.
    assert json.loads(result.stdout) == page


async def test_exclusive_start_stream_name_incompatible_with_page_args(
    api: ApiSession,
) -> None:
    result = await api.run(
        "kinesis list-streams --exclusive-start-stream-name stream-1"
        " --page-size 1",
        expected_rc=252,
    )
    assert "Cannot specify --no-paginate" in result.stderr
    assert "--page-size" in result.stderr
    assert result.calls == ()
