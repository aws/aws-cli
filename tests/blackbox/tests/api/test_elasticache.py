"""ElastiCache commands' requests (upstream tests/functional/elasticache)."""

from typing import Any, Final

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio

CACHE_CLUSTER_ARGS: Final = (
    "elasticache create-cache-cluster"
    " --cache-cluster-id cachecluster-us-east-1c"
    " --num-cache-nodes 1"
    " --cache-node-type cache.m1.small"
    " --engine memcached"
    " --engine-version 1.4.5"
    " --cache-security-group-names group1 group2"
    " --preferred-availability-zone us-east-1c"
    " --preferred-maintenance-window fri:08:00-fri:09:00"
)
CACHE_CLUSTER_PARAMS: Final = {
    "CacheClusterId": "cachecluster-us-east-1c",
    "CacheNodeType": "cache.m1.small",
    "CacheSecurityGroupNames": ["group1", "group2"],
    "Engine": "memcached",
    "EngineVersion": "1.4.5",
    "NumCacheNodes": 1,
    "PreferredAvailabilityZone": "us-east-1c",
    "PreferredMaintenanceWindow": "fri:08:00-fri:09:00",
}
GROUP_ID: Final = "a" * 50
GROUP_DESCRIPTION: Final = "b" * 50


@pytest.mark.parametrize(
    ("flag", "extra_params"),
    [
        pytest.param(
            " --auto-minor-version-upgrade",
            {"AutoMinorVersionUpgrade": True},
            id="auto-minor-upgrade",
        ),
        pytest.param(
            " --no-auto-minor-version-upgrade",
            {"AutoMinorVersionUpgrade": False},
            id="no-auto-minor-upgrade",
        ),
        # Without either flag the request leaves the member out.
        pytest.param("", {}, id="minor-upgrade-arg-not-specified"),
    ],
)
async def test_create_cache_cluster(
    api: ApiSession, flag: str, extra_params: dict[str, Any]
) -> None:
    await api.assert_params_for_cmd(
        CACHE_CLUSTER_ARGS + flag, {**CACHE_CLUSTER_PARAMS, **extra_params}
    )


@pytest.mark.parametrize(
    "option",
    [
        pytest.param("--preferred-cache-cluster-a-zs", id="old-argname"),
        pytest.param("--preferred-cache-cluster-azs", id="fixed-param-name"),
    ],
)
async def test_create_replication_group_preferred_azs(
    api: ApiSession, option: str
) -> None:
    await api.assert_params_for_cmd(
        "elasticache create-replication-group"
        f" --replication-group-id {GROUP_ID}"
        f" --replication-group-description {GROUP_DESCRIPTION}"
        f" {option} az",
        {
            "ReplicationGroupId": GROUP_ID,
            "ReplicationGroupDescription": GROUP_DESCRIPTION,
            "PreferredCacheClusterAZs": ["az"],
        },
    )
