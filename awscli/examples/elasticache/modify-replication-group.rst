**To modify a replication group**

The following ``modify-replication-group`` example modifies the settings for the specified replication group.
For Redis (cluster mode enabled) clusters, this operation cannot be used to change a cluster's node type or engine version. :: 

    aws elasticache modify-replication-group /
        --replication-group-id "my cluster" /
        --replication-group-description "my cluster" /
        --preferred-maintenance-window sun:23:00-mon:01:30 /
        --notification-topic-arn arn:aws:sns:us-west-2:xxxxxxxxxxxxxx52:My_Topic

Output::

    {
        "ReplicationGroup": {
            "ReplicationGroupId": "mycluster",
            "Description": "mycluster",
            "Status": "available",
            "PendingModifiedValues": {},
            "MemberClusters": [
                "mycluster-0001-001",
                "mycluster-0001-002",
                "mycluster-0001-003",
                "mycluster-0003-001",
                "mycluster-0003-002",
                "mycluster-0003-003",
                "mycluster-0004-001",
                "mycluster-0004-002",
                "mycluster-0004-003"
            ],
            "NodeGroups": [
                {
                    "NodeGroupId": "0001",
                    "Status": "available",
                    "Slots": "0-1767,3134-5461,6827-8191",
                    "NodeGroupMembers": [
                        {
                            "CacheClusterId": "mycluster-0001-001",
                            "CacheNodeId": "0001",
                            "PreferredAvailabilityZone": "us-west-2b"
                        },
                        {
                            "CacheClusterId": "mycluster-0001-002",
                            "CacheNodeId": "0001",
                            "PreferredAvailabilityZone": "us-west-2a"
                        },
                        {
                            "CacheClusterId": "mycluster-0001-003",
                            "CacheNodeId": "0001",
                            "PreferredAvailabilityZone": "us-west-2c"
                        }
                    ]
                },
                {
                    "NodeGroupId": "0003",
                    "Status": "available",
                    "Slots": "5462-6826,10923-11075,12441-16383",
                    "NodeGroupMembers": [
                        {
                            "CacheClusterId": "mycluster-0003-001",
                            "CacheNodeId": "0001",
                            "PreferredAvailabilityZone": "us-west-2c"
                        },
                        {
                            "CacheClusterId": "mycluster-0003-002",
                            "CacheNodeId": "0001",
                            "PreferredAvailabilityZone": "us-west-2b"
                        },
                        {
                            "CacheClusterId": "mycluster-0003-003",
                            "CacheNodeId": "0001",
                            "PreferredAvailabilityZone": "us-west-2a"
                        }
                    ]
                },
                {
                    "NodeGroupId": "0004",
                    "Status": "available",
                    "Slots": "1768-3133,8192-10922,11076-12440",
                    "NodeGroupMembers": [
                        {
                            "CacheClusterId": "mycluster-0004-001",
                            "CacheNodeId": "0001",
                            "PreferredAvailabilityZone": "us-west-2b"
                        },
                        {
                            "CacheClusterId": "mycluster-0004-002",
                            "CacheNodeId": "0001",
                            "PreferredAvailabilityZone": "us-west-2a"
                        },
                        {
                            "CacheClusterId": "mycluster-0004-003",
                            "CacheNodeId": "0001",
                            "PreferredAvailabilityZone": "us-west-2c"
                        }
                    ]
                }
            ],
            "AutomaticFailover": "enabled",
            "ConfigurationEndpoint": {
                "Address": "mycluster.xxxxxx.clustercfg.usw2.cache.amazonaws.com",
                "Port": 6379
            },
            "SnapshotRetentionLimit": 1,
            "SnapshotWindow": "13:00-14:00",
            "ClusterEnabled": true,
            "CacheNodeType": "cache.r5.large",
            "TransitEncryptionEnabled": false,
            "AtRestEncryptionEnabled": false
        }
    }

For more information, see `Modifying a Replication Group <https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/Replication.Modify.html`>__ in the *Elasticache User Guide*.
