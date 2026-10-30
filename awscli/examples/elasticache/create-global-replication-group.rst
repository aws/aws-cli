**To create a global replication group**

The following ``create-global-replication-group`` example creates a new global replication group. ::

    aws elasticache create-global-replication-group \
        --global-replication-group-id-suffix my-global-replication-group \
        --primary-replication-group-id my-primary-cluster

Output::

    {
        "GlobalReplicationGroup": {
            "GlobalReplicationGroupId": "sgaui-my-global-replication-group",
            "GlobalReplicationGroupDescription": " ",
            "Status": "creating",
            "CacheNodeType": "cache.r5.large",
            "Engine": "redis",
            "EngineVersion": "5.0.6",
            "Members": [
                {
                    "ReplicationGroupId": "my-primary-cluster",
                    "ReplicationGroupRegion": "us-west-2",
                    "Role": "PRIMARY",
                    "AutomaticFailover": "enabled",
                    "Status": "associating"
                }
            ],
            "ClusterEnabled": true,
            "GlobalNodeGroups": [
                {
                    "GlobalNodeGroupId": "sgaui-my-global-replication-group-0001",
                    "Slots": "0-16383"
                }
            ],
            "AuthTokenEnabled": false,
            "TransitEncryptionEnabled": false,
            "AtRestEncryptionEnabled": false
        }
    }

For more information, see `Replication across AWS Regions using global datastores <https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Redis-Global-Datastore.html>`__ in the *Amazon ElastiCache User Guide*.
