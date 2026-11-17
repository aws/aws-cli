"""Commands that need no profile run with a missing one (upstream
tests/functional/test_args.py)."""

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def missing_profile(api: ApiSession) -> None:
    """Upstream's config, which has profile bar alone, and AWS_PROFILE
    naming a profile it lacks."""
    api.config_path.write_text(
        "[profile bar]\nregion = us-west-2\n", encoding="utf-8"
    )
    api.env["AWS_PROFILE"] = "foo"


async def test_version_ignores_missing_profile(api: ApiSession) -> None:
    run = await api.run("--version")
    assert run.stdout.startswith("aws-cli/"), run.describe()
    assert run.calls == ()


async def test_list_profiles_ignores_missing_profile(api: ApiSession) -> None:
    run = await api.run("configure list-profiles")
    assert run.stdout == "bar\n", run.describe()
    assert run.calls == ()
