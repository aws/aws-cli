"""EC2 commands' requests (upstream tests/functional/ec2)."""

import json
import uuid
from dataclasses import dataclass
from typing import Any, Final

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    ("args", "params"),
    [
        pytest.param(
            "",
            {"InstanceId": "i-12345678", "PublicIp": "192.168.0.0"},
            id="basic",
        ),
        pytest.param(
            " --allocation-id eipalloc-12345678 --allow-reassociation",
            {
                "InstanceId": "i-12345678",
                "PublicIp": "192.168.0.0",
                "AllowReassociation": True,
                "AllocationId": "eipalloc-12345678",
            },
            id="vpc-basic",
        ),
    ],
)
async def test_associate_address_sends_arguments(
    api: ApiSession, args: str, params: dict[str, Any]
) -> None:
    await api.assert_params_for_cmd(
        "ec2 associate-address --instance-id i-12345678"
        " --public-ip 192.168.0.0" + args,
        params,
    )


async def test_create_image_maps_reboot_to_no_reboot(
    api: ApiSession,
) -> None:
    # --reboot is a renamed argument for NoReboot=false.
    await api.assert_params_for_cmd(
        "ec2 create-image --instance-id i-12345678 --description foo"
        " --name bar --reboot",
        {
            "InstanceId": "i-12345678",
            "Description": "foo",
            "Name": "bar",
            "NoReboot": False,
        },
    )


async def test_describe_instance_attribute_sends_both_params(
    api: ApiSession,
) -> None:
    await api.assert_params_for_cmd(
        "ec2 describe-instance-attribute --instance-id i-12345678"
        " --attribute blockDeviceMapping",
        {"InstanceId": "i-12345678", "Attribute": "blockDeviceMapping"},
    )


GROUP_FILTER: Final = {"Name": "group-name", "Values": ["foobar"]}
INSTANCE_FILTER: Final = {"Name": "instance-id", "Values": ["i-12345"]}


@pytest.mark.parametrize(
    ("args", "params"),
    [
        pytest.param([], {}, id="no-params"),
        pytest.param(
            ["--instance-ids", "i-12345678"],
            {"InstanceIds": ["i-12345678"]},
            id="instance-id",
        ),
        pytest.param(
            ["--instance-ids", "i-12345678", "i-87654321"],
            {"InstanceIds": ["i-12345678", "i-87654321"]},
            id="instance-ids",
        ),
        pytest.param(
            ["--instance-ids", '["i-12345678","i-87654321"]'],
            {"InstanceIds": ["i-12345678", "i-87654321"]},
            id="instance-ids-alternate",
        ),
        pytest.param(
            ["--filters", '{"Name":"group-name","Values":["foobar"]}'],
            {"Filters": [GROUP_FILTER]},
            id="filter-json",
        ),
        pytest.param(
            ["--filters", "Name=group-name,Values=foobar"],
            {"Filters": [GROUP_FILTER]},
            id="filter-simple",
        ),
        pytest.param(
            ["--filters", "Name=group-name,Values=foobar,fiebaz"],
            {
                "Filters": [
                    {"Name": "group-name", "Values": ["foobar", "fiebaz"]}
                ]
            },
            id="filter-values",
        ),
        pytest.param(
            [
                "--filters",
                "Name=group-name,Values=foobar",
                "Name=instance-id,Values=i-12345",
            ],
            {"Filters": [GROUP_FILTER, INSTANCE_FILTER]},
            id="multiple-filters",
        ),
        # Shorthand tolerates spaces around its separators.
        pytest.param(
            [
                "--filters",
                "Name = group-name, Values= foobar",
                "Name=instance-id,Values=i-12345",
            ],
            {"Filters": [GROUP_FILTER, INSTANCE_FILTER]},
            id="multiple-filters-alternate",
        ),
        pytest.param(
            ["--page-size", "10"], {"MaxResults": 10}, id="page-size"
        ),
    ],
)
async def test_describe_instances_sends_arguments(
    api: ApiSession, args: list[str], params: dict[str, Any]
) -> None:
    await api.assert_params_for_cmd(
        ["ec2", "describe-instances", *args], params
    )


@dataclass(frozen=True)
class Listing:
    """A describe command that pages 1000 results at a time unless the
    request names what it describes."""

    command: str
    ids_option: str
    ids_member: str
    resource_id: str
    filter_name: str
    filter_value: str


LISTINGS: Final = [
    pytest.param(
        Listing(
            "describe-snapshots",
            "--snapshot-ids",
            "SnapshotIds",
            "snap-example",
            "snapshot-id",
            "snap-snap",
        ),
        id="snapshots",
    ),
    pytest.param(
        Listing(
            "describe-volumes",
            "--volume-ids",
            "VolumeIds",
            "id-volume",
            "volume-id",
            "id-volume",
        ),
        id="volumes",
    ),
]


@pytest.mark.parametrize("listing", LISTINGS)
async def test_max_results_set_by_default(
    api: ApiSession, listing: Listing
) -> None:
    await api.assert_params_for_cmd(
        f"ec2 {listing.command}", {"MaxResults": 1000}
    )


@pytest.mark.parametrize("listing", LISTINGS)
async def test_max_results_not_set_with_ids(
    api: ApiSession, listing: Listing
) -> None:
    await api.assert_params_for_cmd(
        f"ec2 {listing.command} {listing.ids_option} {listing.resource_id}",
        {listing.ids_member: [listing.resource_id]},
    )


@pytest.mark.parametrize("listing", LISTINGS)
async def test_max_results_not_set_with_filter(
    api: ApiSession, listing: Listing
) -> None:
    name, value = listing.filter_name, listing.filter_value
    await api.assert_params_for_cmd(
        f"ec2 {listing.command} --filters Name={name},Values={value}",
        {"Filters": [{"Name": name, "Values": [value]}]},
    )


@pytest.mark.parametrize(
    "args",
    [
        pytest.param("--max-results 5", id="max-results"),
        pytest.param("--page-size 5", id="page-size"),
    ],
)
@pytest.mark.parametrize("listing", LISTINGS)
async def test_max_results_not_overwritten(
    api: ApiSession, listing: Listing, args: str
) -> None:
    await api.assert_params_for_cmd(
        f"ec2 {listing.command} {args}", {"MaxResults": 5}
    )


async def test_describe_volumes_reads_cli_input_json(
    api: ApiSession,
) -> None:
    params = {"VolumeIds": ["vol-12345"]}
    path = api.cwd / "params.json"
    path.write_text(json.dumps(params), encoding="utf-8")
    await api.assert_params_for_cmd(
        ["ec2", "describe-volumes", "--cli-input-json", f"file://{path}"],
        params,
    )


async def test_get_password_data_rejects_missing_launch_key(
    api: ApiSession,
) -> None:
    result = await api.assert_params_for_cmd(
        "ec2 get-password-data --instance-id i-12345678"
        " --priv-launch-key foo.pem",
        expected_rc=255,
        stderr_contains=(
            "priv-launch-key should be a path to the local SSH private key"
            " file used to launch the instance.\n"
        ),
    )
    assert result.calls == ()


async def test_modify_image_attribute_names_bad_json_argument(
    api: ApiSession,
) -> None:
    result = await api.assert_params_for_cmd(
        "ec2 modify-image-attribute --image-id ami-d00dbeef"
        " --launch-permission THISISNOTJSON",
        expected_rc=252,
        stderr_contains="launch-permission",
    )
    assert result.calls == ()


@pytest.mark.parametrize(
    "flags",
    [
        pytest.param(
            "--no-ebs-optimized --ebs-optimized Value=true",
            id="value-and-non-value",
        ),
        pytest.param(
            "--no-ebs-optimized --ebs-optimized", id="non-value-bools"
        ),
    ],
)
async def test_modify_instance_attribute_rejects_mixed_bool_forms(
    api: ApiSession, flags: str
) -> None:
    result = await api.assert_params_for_cmd(
        f"ec2 modify-instance-attribute --instance-id i-1234 {flags}",
        expected_rc=252,
        stderr_contains="Cannot specify both",
    )
    assert result.calls == ()


ONE_INSTANCE: Final = {"ImageId": "ami-foobar", "MaxCount": 1, "MinCount": 1}
SUBNET: Final = "subnet-12345678"


def primary_interface(**members: Any) -> dict[str, Any]:
    """The request's one network interface, device 0, with `members`."""
    return {"NetworkInterfaces": [{"DeviceIndex": 0, **members}]}


def secondary_addresses(*addresses: str) -> list[dict[str, Any]]:
    return [
        {"Primary": False, "PrivateIpAddress": address}
        for address in addresses
    ]


async def assert_run_instances_call(
    api: ApiSession, args: str | list[str], params: dict[str, Any]
) -> None:
    """Upstream's helper: the request, less its idempotency token, which
    botocore fills with a random UUID."""
    argv = args.split() if isinstance(args, str) else args
    result = await api.assert_params_for_cmd(
        ["ec2", "run-instances", *argv], params, ignore_params=["ClientToken"]
    )
    assert result.last_params is not None
    uuid.UUID(result.last_params["ClientToken"])


@pytest.mark.parametrize(
    ("args", "params"),
    [
        pytest.param(
            "--image-id ami-foobar", ONE_INSTANCE, id="no-count"
        ),
        pytest.param(
            "--image-id ami-foobar --count 2",
            {**ONE_INSTANCE, "MaxCount": 2, "MinCount": 2},
            id="count-scalar",
        ),
        pytest.param(
            "--image-id ami-foobar --count 5:10",
            {**ONE_INSTANCE, "MaxCount": 10, "MinCount": 5},
            id="count-range",
        ),
        pytest.param(
            '--cli-input-json {"ImageId":"ami-xxxx","MaxCount":9,'
            '"MinCount":5}',
            {"ImageId": "ami-xxxx", "MaxCount": 9, "MinCount": 5},
            id="count-in-json-only",
        ),
        pytest.param(
            '--count 3 --cli-input-json {"ImageId":"ami-xxxx","MaxCount":9,'
            '"MinCount":5}',
            {"ImageId": "ami-xxxx", "MaxCount": 3, "MinCount": 3},
            id="count-in-cli-and-in-json",
        ),
        pytest.param(
            "--image-id ami-foobar --count 1"
            " --secondary-private-ip-addresses 10.0.2.106",
            {
                **ONE_INSTANCE,
                **primary_interface(
                    PrivateIpAddresses=secondary_addresses("10.0.2.106")
                ),
            },
            id="secondary-ip-address",
        ),
        pytest.param(
            f"--image-id ami-foobar --count 1 --subnet {SUBNET}"
            " --secondary-private-ip-addresses 10.0.2.106",
            {
                **ONE_INSTANCE,
                **primary_interface(
                    SubnetId=SUBNET,
                    PrivateIpAddresses=secondary_addresses("10.0.2.106"),
                ),
            },
            id="secondary-ip-address-with-subnet",
        ),
        pytest.param(
            "--image-id ami-foobar --count 1"
            " --secondary-private-ip-addresses 10.0.2.106 10.0.2.107",
            {
                **ONE_INSTANCE,
                **primary_interface(
                    PrivateIpAddresses=secondary_addresses(
                        "10.0.2.106", "10.0.2.107"
                    )
                ),
            },
            id="secondary-ip-addresses",
        ),
        pytest.param(
            "--image-id ami-foobar --count 1"
            " --secondary-private-ip-address-count 4",
            {
                **ONE_INSTANCE,
                **primary_interface(SecondaryPrivateIpAddressCount=4),
            },
            id="secondary-ip-address-count",
        ),
        pytest.param(
            f"--image-id ami-foobar --count 1 --subnet {SUBNET}"
            " --secondary-private-ip-address-count 4",
            {
                **ONE_INSTANCE,
                **primary_interface(
                    SubnetId=SUBNET, SecondaryPrivateIpAddressCount=4
                ),
            },
            id="secondary-ip-address-count-with-subnet",
        ),
        pytest.param(
            f"--image-id ami-foobar --count 1 --subnet-id {SUBNET}"
            " --associate-public-ip-address",
            {
                **ONE_INSTANCE,
                **primary_interface(
                    AssociatePublicIpAddress=True, SubnetId=SUBNET
                ),
            },
            id="associate-public-ip-address",
        ),
        pytest.param(
            "--image-id ami-foobar --count 1"
            f" --associate-public-ip-address --subnet-id {SUBNET}",
            {
                **ONE_INSTANCE,
                **primary_interface(
                    AssociatePublicIpAddress=True, SubnetId=SUBNET
                ),
            },
            id="associate-public-ip-address-switch-order",
        ),
        pytest.param(
            f"--image-id ami-foobar --count 1  --subnet-id {SUBNET}"
            " --no-associate-public-ip-address",
            {
                **ONE_INSTANCE,
                **primary_interface(
                    AssociatePublicIpAddress=False, SubnetId=SUBNET
                ),
            },
            id="no-associate-public-ip-address",
        ),
        pytest.param(
            f"--image-id ami-foobar --count 1 --subnet-id {SUBNET}",
            {**ONE_INSTANCE, "SubnetId": SUBNET},
            id="subnet-alone",
        ),
        pytest.param(
            "--image-id ami-foobar --count 1 --security-group-id sg-12345678"
            f" --associate-public-ip-address --subnet-id {SUBNET}",
            {
                **ONE_INSTANCE,
                **primary_interface(
                    AssociatePublicIpAddress=True,
                    SubnetId=SUBNET,
                    Groups=["sg-12345678"],
                ),
            },
            id="associate-public-ip-address-and-group-id",
        ),
        pytest.param(
            "--image-id ami-foobar --count 1 --security-group-id sg-12345678",
            {**ONE_INSTANCE, "SecurityGroupIds": ["sg-12345678"]},
            id="group-id-alone",
        ),
        pytest.param(
            "--image-id ami-foobar --count 1 --private-ip-address 10.0.0.200"
            f" --associate-public-ip-address --subnet-id {SUBNET}",
            {
                **ONE_INSTANCE,
                **primary_interface(
                    AssociatePublicIpAddress=True,
                    SubnetId=SUBNET,
                    PrivateIpAddresses=[
                        {"PrivateIpAddress": "10.0.0.200", "Primary": True}
                    ],
                ),
            },
            id="associate-public-ip-address-and-private-ip-address",
        ),
        pytest.param(
            "--image-id ami-foobar --count 1 --private-ip-address 10.0.0.200",
            {**ONE_INSTANCE, "PrivateIpAddress": "10.0.0.200"},
            id="private-ip-address-alone",
        ),
        pytest.param(
            "--associate-public-ip-address --ipv6-address-count 5"
            " --image-id ami-foobar --count 1",
            {
                **ONE_INSTANCE,
                **primary_interface(
                    AssociatePublicIpAddress=True, Ipv6AddressCount=5
                ),
            },
            id="ipv6-address-count-and-associate-public-ip-address",
        ),
        pytest.param(
            "--associate-public-ip-address --count 1"
            " --ipv6-addresses Ipv6Address=::1 --image-id ami-foobar",
            {
                **ONE_INSTANCE,
                **primary_interface(
                    AssociatePublicIpAddress=True,
                    Ipv6Addresses=[{"Ipv6Address": "::1"}],
                ),
            },
            id="ipv6-addresses-and-associate-public-ip-address",
        ),
        pytest.param(
            "--associate-public-ip-address --enable-primary-ipv6"
            " --image-id ami-foobar --count 1",
            {
                **ONE_INSTANCE,
                **primary_interface(
                    AssociatePublicIpAddress=True, PrimaryIpv6=True
                ),
            },
            id="enable-primary-ipv6-and-associate-public-ip-address",
        ),
    ],
)
async def test_run_instances_sends_arguments(
    api: ApiSession, args: str, params: dict[str, Any]
) -> None:
    await assert_run_instances_call(api, args, params)


async def test_run_instances_keeps_leading_space_in_json(
    api: ApiSession,
) -> None:
    await assert_run_instances_call(
        api,
        [
            "--image-id",
            "ami-foobar",
            "--count",
            "1",
            "--block-device-mapping",
            ' [{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":20}}]',
        ],
        {
            **ONE_INSTANCE,
            "BlockDeviceMappings": [
                {"DeviceName": "/dev/sda1", "Ebs": {"VolumeSize": 20}}
            ],
        },
    )


async def test_run_instances_encodes_user_data_file(api: ApiSession) -> None:
    path = api.cwd / "user-data"
    path.write_text("\u0039", encoding="utf-8")
    await assert_run_instances_call(
        api,
        ["--image-id", "foo", "--user-data", f"file://{path}"],
        # The base64 of the file's UTF-8 bytes.
        {"ImageId": "foo", "MaxCount": 1, "MinCount": 1, "UserData": "OQ=="},
    )


def ip_permission(**members: Any) -> dict[str, Any]:
    """The request for one permission on group foobar."""
    return {"GroupName": "foobar", "IpPermissions": [members]}


ANY_CIDR: Final = [{"CidrIp": "0.0.0.0/0"}]
JSON_PERMISSIONS: Final = (
    '[{"FromPort":8000,"ToPort":9000,"IpProtocol":"tcp",'
    '"IpRanges":[{"CidrIp":"192.168.100.0/24"}]}]'
)
JSON_PERMISSION: Final = {
    "FromPort": 8000,
    "ToPort": 9000,
    "IpProtocol": "tcp",
    "IpRanges": [{"CidrIp": "192.168.100.0/24"}],
}
INGRESS_COMMANDS: Final = [
    pytest.param("authorize-security-group-ingress", id="authorize"),
    pytest.param("revoke-security-group-ingress", id="revoke"),
]


@pytest.mark.parametrize(
    ("args", "params"),
    [
        pytest.param(
            "--group-name foobar --protocol tcp --port 22-25"
            " --cidr 0.0.0.0/0",
            ip_permission(
                FromPort=22, IpProtocol="tcp", IpRanges=ANY_CIDR, ToPort=25
            ),
            id="simple-cidr",
        ),
        pytest.param(
            "--group-name foobar --protocol tcp --port all --cidr 0.0.0.0/0",
            ip_permission(
                FromPort=-1, IpProtocol="tcp", IpRanges=ANY_CIDR, ToPort=-1
            ),
            id="all-port",
        ),
        # From port 8 to port -1: an ICMP echo request.
        pytest.param(
            "--group-name foobar --protocol tcp --port 8--1 --cidr 0.0.0.0/0",
            ip_permission(
                FromPort=8, IpProtocol="tcp", IpRanges=ANY_CIDR, ToPort=-1
            ),
            id="icmp-echo-request",
        ),
        # IpProtocol is modeled as a string, so "all" is the string "-1".
        pytest.param(
            "--group-name foobar --protocol all --port all --cidr 0.0.0.0/0",
            ip_permission(
                FromPort=-1, IpProtocol="-1", IpRanges=ANY_CIDR, ToPort=-1
            ),
            id="all-protocol",
        ),
        pytest.param(
            "--group-name foobar --protocol 200 --cidr 0.0.0.0/0",
            ip_permission(IpProtocol="200", IpRanges=ANY_CIDR),
            id="numeric-protocol",
        ),
        pytest.param(
            "--group-name foobar --protocol -1 --cidr 0.0.0.0/0",
            ip_permission(IpProtocol="-1", IpRanges=ANY_CIDR),
            id="negative-one-protocol",
        ),
        pytest.param(
            "--group-name foobar --protocol udp --source-group fiebaz"
            " --group-owner 11111111",
            ip_permission(
                IpProtocol="udp",
                UserIdGroupPairs=[
                    {"GroupName": "fiebaz", "UserId": "11111111"}
                ],
            ),
            id="classic-group",
        ),
        pytest.param(
            "--group-name foobar --protocol icmp --source-group sg-12345678",
            ip_permission(
                IpProtocol="icmp",
                UserIdGroupPairs=[{"GroupId": "sg-12345678"}],
            ),
            id="vpc-group",
        ),
        pytest.param(
            f"--group-name foobar --ip-permissions {JSON_PERMISSIONS}",
            ip_permission(**JSON_PERMISSION),
            id="IpPermissions",
        ),
        pytest.param(
            f"--group-id sg-12345678 --ip-permissions {JSON_PERMISSIONS}",
            {"GroupId": "sg-12345678", "IpPermissions": [JSON_PERMISSION]},
            id="IpPermissions-with-group-id",
        ),
    ],
)
@pytest.mark.parametrize("command", INGRESS_COMMANDS)
async def test_security_group_ingress_builds_ip_permissions(
    api: ApiSession, command: str, args: str, params: dict[str, Any]
) -> None:
    await api.assert_params_for_cmd(f"ec2 {command} {args}", params)


@pytest.mark.parametrize("command", INGRESS_COMMANDS)
async def test_security_group_ingress_rejects_port_with_ip_permissions(
    api: ApiSession, command: str
) -> None:
    result = await api.assert_params_for_cmd(
        f"ec2 {command} --group-name foobar --port 100"
        f" --ip-permissions {JSON_PERMISSIONS}",
        expected_rc=252,
    )
    assert result.calls == ()
