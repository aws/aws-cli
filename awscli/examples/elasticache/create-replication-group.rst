**To create a replication group**

The following ``create-replication-group`` example creates a Valkey (cluster mode disabled) replication group with in-transit encryption enabled. This operation is valid for Valkey and Redis OSS. For Valkey, you must specify ``--transit-encryption-enabled`` or ``--no-transit-encryption-enabled``. ::

    aws elasticache create-replication-group \
        --replication-group-id "mygroup" \
        --replication-group-description "my group" \
        --engine "valkey" \
        --cache-node-type "cache.m7g.large" \
        --transit-encryption-enabled

Output::

    {
        "ReplicationGroup": {
            "ReplicationGroupId": "mygroup",
            "Description": "my group",
            "GlobalReplicationGroupInfo": {},
            "Status": "creating",
            "PendingModifiedValues": {},
            "MemberClusters": [
                "mygroup-001"
            ],
            "AutomaticFailover": "disabled",
            "MultiAZ": "disabled",
            "SnapshotRetentionLimit": 0,
            "SnapshotWindow": "09:30-10:30",
            "ClusterEnabled": false,
            "CacheNodeType": "cache.m7g.large",
            "TransitEncryptionEnabled": true,
            "AtRestEncryptionEnabled": true,
            "ARN": "arn:aws:elasticache:us-west-2:123456789012:replicationgroup:mygroup",
            "LogDeliveryConfigurations": [],
            "ReplicationGroupCreateTime": "2026-10-26T14:21:45.460000+00:00",
            "DataTiering": "disabled",
            "AutoMinorVersionUpgrade": true,
            "NetworkType": "ipv4",
            "IpDiscovery": "ipv4",
            "TransitEncryptionMode": "required",
            "ClusterMode": "disabled",
            "Engine": "valkey"
        }
    }

For more information, see `Creating a Valkey or Redis OSS replication group <https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Replication.CreatingRepGroup.html>`__ in the *Amazon ElastiCache User Guide*.
