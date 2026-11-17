"""Table output's colors (upstream tests/functional/test_table.py)."""

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio


async def test_color_on_colors_piped_table(api: ApiSession) -> None:
    run = await api.run(
        "s3api list-buckets --output table --color on",
        replies={
            "Owner": {"DisplayName": "foo", "ID": "bar"},
            "Buckets": [
                {
                    "CreationDate": "2016-06-15T16:49:44.000Z",
                    "Name": "foo-bucket",
                }
            ],
        },
    )
    # ESC starts every ANSI color sequence; stdout is a pipe here.
    assert "\x1b" in run.stdout, run.describe()
