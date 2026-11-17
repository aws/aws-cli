"""CloudWatch Logs commands: get-log-events' options and tail's requests
and output (upstream tests/functional/logs)."""

import time
from collections.abc import Mapping
from typing import Any, Final

import pytest

from apihelpers import ApiSession, CommandRun

pytestmark = pytest.mark.asyncio

GROUP: Final = "mygroup"
STREAM: Final = "mystream"
MESSAGE: Final = "my message\n"
# 1.1 seconds after the epoch, as tail prints it in each format.
EVENT_MILLIS: Final = 1100
TIMESTAMP: Final = "1970-01-01T00:00:01.100000+00:00"
SHORT_TIMESTAMP: Final = "1970-01-01T00:00:01"
LINE: Final = f"{TIMESTAMP} {STREAM} {MESSAGE}"
TEN_MINUTES_MILLIS: Final = 10 * 60 * 1000


def page(event_id: str, **extra: Any) -> dict[str, Any]:
    """A FilterLogEvents page holding one event."""
    event = {
        "eventId": event_id,
        "logStreamName": STREAM,
        "message": MESSAGE,
        "timestamp": EVENT_MILLIS,
        "ingestionTime": EVENT_MILLIS,
    }
    return {"events": [event], **extra}


async def run_tail(
    api: ApiSession, args: str, replies: list[Mapping[str, Any]]
) -> tuple[CommandRun, range]:
    """Run `logs tail` and return it with the start times, in epoch
    milliseconds, that its default --since of 10m can resolve to."""
    before = time.time()
    result = await api.run(f"logs tail {GROUP}{args}", replies=replies)
    after = time.time()
    # One millisecond of slack below for float rounding.
    window = range(
        int(before * 1000) - TEN_MINUTES_MILLIS - 1,
        int(after * 1000) - TEN_MINUTES_MILLIS + 1,
    )
    return result, window


def split_start_time(params: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    """A request's startTime and its other parameters."""
    rest = dict(params)
    return rest.pop("startTime", None), rest


async def test_get_log_events_cannot_paginate(api: ApiSession) -> None:
    result = await api.run(
        "logs get-log-events --log-group-name foo --log-stream-name bar"
        " --page-size 5",
        expected_rc=252,
    )
    assert "Unknown options" in result.stderr
    assert "--page-size" in result.stderr
    assert result.calls == ()


@pytest.mark.parametrize(
    ("args", "extra_params"),
    [
        pytest.param("", {}, id="no-options"),
        pytest.param(
            " --filter-pattern Pattern",
            {"filterPattern": "Pattern"},
            id="filter-pattern",
        ),
        pytest.param(
            " --log-stream-names foo-stream bar-stream",
            {"logStreamNames": ["foo-stream", "bar-stream"]},
            id="log-stream-names",
        ),
        pytest.param(
            " --log-stream-name-prefix foo",
            {"logStreamNamePrefix": "foo"},
            id="log-stream-name-prefix",
        ),
    ],
)
async def test_tail(
    api: ApiSession, args: str, extra_params: dict[str, Any]
) -> None:
    result, window = await run_tail(api, args, [page("event1")])
    assert result.operations == ["FilterLogEvents"]
    start_time, params = split_start_time(result.calls[0].params)
    assert start_time in window
    assert params == {
        "logGroupName": GROUP,
        "interleaved": True,
        **extra_params,
    }
    assert result.stdout == LINE


async def test_tail_paginated(api: ApiSession) -> None:
    result, window = await run_tail(
        api, "", [page("event1", nextToken="token"), page("event2")]
    )
    assert result.operations == ["FilterLogEvents", "FilterLogEvents"]
    first_start, first = split_start_time(result.calls[0].params)
    second_start, second = split_start_time(result.calls[1].params)
    assert first_start in window
    assert second_start == first_start
    assert first == {"logGroupName": GROUP, "interleaved": True}
    assert second == {
        "logGroupName": GROUP,
        "interleaved": True,
        "nextToken": "token",
    }
    assert result.stdout == LINE * 2


async def test_tail_with_since(api: ApiSession) -> None:
    # A timestamp without a zone is UTC: one second after the epoch.
    await api.assert_params_for_cmd(
        f"logs tail {GROUP} --since 1970-01-01T00:00:01",
        {"logGroupName": GROUP, "interleaved": True, "startTime": 1000},
        replies=[page("event1")],
    )


@pytest.mark.parametrize(
    ("args", "stdout"),
    [
        pytest.param(
            " --format short",
            f"{SHORT_TIMESTAMP} {MESSAGE}",
            id="short-format",
        ),
        pytest.param(
            " --color on",
            f"\x1b[32m{TIMESTAMP}\x1b[0m \x1b[36m{STREAM}\x1b[0m {MESSAGE}",
            id="color-on",
        ),
        pytest.param(" --color off", LINE, id="color-off"),
    ],
)
async def test_tail_output(api: ApiSession, args: str, stdout: str) -> None:
    result, _ = await run_tail(api, args, [page("event1")])
    assert result.operations == ["FilterLogEvents"]
    assert result.stdout == stdout
