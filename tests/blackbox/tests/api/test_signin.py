"""Sign-In's renamed OAuth2 commands (upstream tests/functional/signin)."""

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio


# create-o-auth2-token shipped before the rename, so it stays an alias.
@pytest.mark.parametrize(
    "command", ["create-o-auth2-token", "create-oauth2-token"]
)
async def test_create_oauth2_token_runs_under_both_names(
    api: ApiSession, command: str
) -> None:
    run = await api.run(
        f"signin {command} --token-input"
        " clientId=c,grantType=authorization_code"
    )
    assert run.operations == ["CreateOAuth2Token"], run.describe()


async def test_create_oauth2_token_with_iam_has_only_the_new_name(
    api: ApiSession,
) -> None:
    args = "--grant-type client_credentials --resource r"
    run = await api.run(f"signin create-oauth2-token-with-iam {args}")
    assert run.operations == ["CreateOAuth2TokenWithIAM"], run.describe()
    run = await api.run(
        f"signin create-o-auth2-token-with-iam {args}", expected_rc=252
    )
    assert run.calls == ()
