"""SES send-email's requests (upstream tests/functional/ses)."""

from typing import Any, Final

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio

PREFIX: Final = "ses send-email --subject This_is_a_test --from foo@bar.com"
JSON_MESSAGE: Final = (
    '--message {"Subject":{"Data":"This_is_a_test"},'
    '"Body":{"Text":{"Data":"This_is_the_message"}}}'
    " --from foo@bar.com"
    ' --destination {"ToAddresses":["fie@baz.com"]}'
)
SUBJECT: Final = {"Subject": {"Data": "This_is_a_test"}}
TEXT_BODY: Final = {"Text": {"Data": "This_is_the_message"}}


@pytest.mark.parametrize(
    ("args", "params"),
    [
        pytest.param(
            f"{PREFIX} --to fie@baz.com --text This_is_the_message",
            {
                "Source": "foo@bar.com",
                "Destination": {"ToAddresses": ["fie@baz.com"]},
                "Message": {"Body": TEXT_BODY, **SUBJECT},
            },
            id="plain-text",
        ),
        pytest.param(
            f"{PREFIX} --to fie1@baz.com fie2@baz.com"
            " --text This_is_the_message",
            {
                "Source": "foo@bar.com",
                "Destination": {
                    "ToAddresses": ["fie1@baz.com", "fie2@baz.com"]
                },
                "Message": {"Body": TEXT_BODY, **SUBJECT},
            },
            id="plain-text-multiple-to",
        ),
        pytest.param(
            f"{PREFIX} --to fie1@baz.com fie2@baz.com"
            " --text This_is_the_message --cc fie3@baz.com fie4@baz.com",
            {
                "Source": "foo@bar.com",
                "Destination": {
                    "CcAddresses": ["fie3@baz.com", "fie4@baz.com"],
                    "ToAddresses": ["fie1@baz.com", "fie2@baz.com"],
                },
                "Message": {"Body": TEXT_BODY, **SUBJECT},
            },
            id="plain-text-multiple-cc",
        ),
        pytest.param(
            f"{PREFIX} --to fie1@baz.com fie2@baz.com"
            " --text This_is_the_message --cc fie3@baz.com fie4@baz.com"
            " --bcc fie5@baz.com fie6@baz.com",
            {
                "Source": "foo@bar.com",
                "Destination": {
                    "BccAddresses": ["fie5@baz.com", "fie6@baz.com"],
                    "CcAddresses": ["fie3@baz.com", "fie4@baz.com"],
                    "ToAddresses": ["fie1@baz.com", "fie2@baz.com"],
                },
                "Message": {"Body": TEXT_BODY, **SUBJECT},
            },
            id="plain-text-multiple-bcc",
        ),
        pytest.param(
            f"{PREFIX} --to fie@baz.com --html This_is_the_html_message",
            {
                "Source": "foo@bar.com",
                "Destination": {"ToAddresses": ["fie@baz.com"]},
                "Message": {
                    "Body": {"Html": {"Data": "This_is_the_html_message"}},
                    **SUBJECT,
                },
            },
            id="html-text",
        ),
        pytest.param(
            f"{PREFIX} --to fie@baz.com --html This_is_the_html_message"
            " --text This_is_the_text_message",
            {
                "Source": "foo@bar.com",
                "Destination": {"ToAddresses": ["fie@baz.com"]},
                "Message": {
                    "Body": {
                        "Text": {"Data": "This_is_the_text_message"},
                        "Html": {"Data": "This_is_the_html_message"},
                    },
                    **SUBJECT,
                },
            },
            id="html-both",
        ),
        pytest.param(
            f"ses send-email {JSON_MESSAGE}",
            {
                "Destination": {"ToAddresses": ["fie@baz.com"]},
                "Message": {"Body": TEXT_BODY, **SUBJECT},
                "Source": "foo@bar.com",
            },
            id="using-json",
        ),
    ],
)
async def test_send_email_sends_params(
    api: ApiSession, args: str, params: dict[str, Any]
) -> None:
    run = await api.assert_params_for_cmd(args, params)
    assert run.operations == ["SendEmail"]


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(
            f"ses send-email {JSON_MESSAGE} --to fie2@baz.com",
            id="both-destination-and-to",
        ),
        pytest.param(
            f"ses send-email {JSON_MESSAGE} --text This_is_another_body",
            id="both-message-and-text",
        ),
    ],
)
async def test_send_email_rejects_conflicting_args(
    api: ApiSession, args: str
) -> None:
    run = await api.run(args, expected_rc=252)
    assert run.calls == ()
