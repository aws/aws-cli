"""Route 53 commands' requests (upstream tests/functional/route53)."""

from typing import Any, Final

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio

CHANGE_BATCH_JSON: Final = (
    '{"Comment":"string","Changes":['
    '{"Action":"CREATE","ResourceRecordSet":{'
    '"Name":"test-foo.bar.com",'
    '"Type":"CNAME",'
    '"TTL":300,'
    '"ResourceRecords":['
    '{"Value":"foo-bar-com"}'
    "]}}]}"
)


@pytest.mark.parametrize(
    ("args", "params"),
    [
        pytest.param(
            "--hosted-zone-id /hostedzone/ZD3IYMVP1KDDM",
            {"HostedZoneId": "ZD3IYMVP1KDDM"},
            id="no-pagination-args",
        ),
        # --max-items is the CLI's paginator limit, not the service's.
        pytest.param(
            "--hosted-zone-id /hostedzone/ZD3IYMVP1KDDM --max-items 1",
            {"HostedZoneId": "ZD3IYMVP1KDDM"},
            id="max-items",
        ),
        pytest.param(
            "--hosted-zone-id /hostedzone/ABCD --max-items 1",
            {"HostedZoneId": "ABCD"},
            id="max-items-full-resource-id",
        ),
        # --start-record-name turns pagination off, so --max-items goes to
        # the service.
        pytest.param(
            "--hosted-zone-id /hostedzone/ZD3IYMVP1KDDM --max-items 1"
            " --start-record-name foo",
            {
                "HostedZoneId": "ZD3IYMVP1KDDM",
                "StartRecordName": "foo",
                "MaxItems": "1",
            },
            id="start-record-name-disables-pagination",
        ),
    ],
)
async def test_list_resource_record_sets_sends_params(
    api: ApiSession, args: str, params: dict[str, Any]
) -> None:
    run = await api.assert_params_for_cmd(
        f"route53 list-resource-record-sets {args}", params
    )
    assert run.operations == ["ListResourceRecordSets"]


@pytest.mark.parametrize(
    ("command", "resource_id", "expected_id"),
    [
        pytest.param(
            "get-hosted-zone",
            "/hostedzone/ZD3IYMVP1KDDM",
            "ZD3IYMVP1KDDM",
            id="hosted-zone-full",
        ),
        pytest.param(
            "get-hosted-zone",
            "ZD3IYMVP1KDDM",
            "ZD3IYMVP1KDDM",
            id="hosted-zone-short",
        ),
        pytest.param(
            "get-change",
            "/change/ZD3IYMVP1KDDM",
            "ZD3IYMVP1KDDM",
            id="change-full",
        ),
        pytest.param(
            "get-change",
            "ZD3IYMVP1KDDM",
            "ZD3IYMVP1KDDM",
            id="change-short",
        ),
        pytest.param(
            "get-reusable-delegation-set",
            "/delegationset/N9INWVYQ6Q0FN",
            "N9INWVYQ6Q0FN",
            id="delegation-set-full",
        ),
        pytest.param(
            "get-reusable-delegation-set",
            "N9INWVYQ6Q0FN",
            "N9INWVYQ6Q0FN",
            id="delegation-set-short",
        ),
    ],
)
async def test_resource_id_prefix_is_stripped(
    api: ApiSession, command: str, resource_id: str, expected_id: str
) -> None:
    await api.assert_params_for_cmd(
        f"route53 {command} --id {resource_id}", {"Id": expected_id}
    )


async def test_change_resource_record_sets_strips_hosted_zone_prefix(
    api: ApiSession,
) -> None:
    await api.assert_params_for_cmd(
        "route53 change-resource-record-sets"
        " --hosted-zone-id /change/ZD3IYMVP1KDDM"
        f" --change-batch {CHANGE_BATCH_JSON}",
        {
            "HostedZoneId": "ZD3IYMVP1KDDM",
            "ChangeBatch": {
                "Comment": "string",
                "Changes": [
                    {
                        "Action": "CREATE",
                        "ResourceRecordSet": {
                            "Name": "test-foo.bar.com",
                            "Type": "CNAME",
                            "TTL": 300,
                            "ResourceRecords": [{"Value": "foo-bar-com"}],
                        },
                    }
                ],
            },
        },
    )
