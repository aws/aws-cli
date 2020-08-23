**To describe replication groups**

The following ``describe-replication-groups`` example returns information about the specified replication group. ::

    aws elasticache describe-replication-groups 
        --replication-group-id "my-cluster"

Output::

    {
        "ReplicationGroups": [
            {
                "ReplicationGroupId": "my-cluster",
                "Description": "mycluster",
                "Status": "available",
                "PendingModifiedValues": {},
                "MemberClusters": [
                    "pat-cluster-001",
                    "pat-cluster-002",
                    "pat-cluster-003",
                    "pat-cluster-004"
                ],
                "NodeGroups": [
                    {
                        "NodeGroupId": "0001",
                        "Status": "available",
                        "PrimaryEndpoint": {
                            "Address": "my-cluster.xxxxih.ng.0001.usw2.cache.amazonaws.com",
                            "Port": 6379
                        },
                        "ReaderEndpoint": {
                            "Address": "my-cluster-ro.xxxxih.ng.0001.usw2.cache.amazonaws.com",
                            "Port": 6379
                        },
                        "NodeGroupMembers": [
                            {
                                "CacheClusterId": "my-cluster-001",
                                "CacheNodeId": "0001",
                                "ReadEndpoint": {
                                    "Address": "pat-cluster-001.xxxih.0001.usw2.cache.amazonaws.com",
                                    "Port": 6379
                                },
                                "PreferredAvailabilityZone": "us-west-2a",
                                "CurrentRole": "primary"
                            },
                            {
                                "CacheClusterId": "my-cluster-002",
                                "CacheNodeId": "0001",
                                "ReadEndpoint": {
                                    "Address": "pat-cluster-002.xxxxih.0001.usw2.cache.amazonaws.com",
                                    "Port": 6379
                                },
                                "PreferredAvailabilityZone": "us-west-2a",
                                "CurrentRole": "replica"
                            },
                            {
                                "CacheClusterId": "my-cluster-003",
                                "CacheNodeId": "0001",
                                "ReadEndpoint": {
                                    "Address": "pat-cluster-003.xxxxih.0001.usw2.cache.amazonaws.com",
                                    "Port": 6379
                                },
                                "PreferredAvailabilityZone": "us-west-2a",
                                "CurrentRole": "replica"
                            },
                            {
                                "CacheClusterId": "my-cluster-004",
                                "CacheNodeId": "0001",
                                "ReadEndpoint": {
                                    "Address": "pat-cluster-004.xxxih.0001.usw2.cache.amazonaws.com",
                                    "Port": 6379
                                },
                                "PreferredAvailabilityZone": "us-west-2a",
                                "CurrentRole": "replica"
                            }
                        ]
                    }
                ],
                "AutomaticFailover": "disabled",
                "SnapshotRetentionLimit": 0,
                "SnapshotWindow": "07:30-08:30",
                "ClusterEnabled": false,
                "CacheNodeType": "cache.r5.xlarge",
                "AuthTokenEnabled": false,
                "TransitEncryptionEnabled": false,
                "AtRestEncryptionEnabled": false
            }
        ]
    }

For more information, see `Viewing a Replication Group's Details <https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/Replication.ViewDetails.html>`__ in the *Elasticache User Guide*.
