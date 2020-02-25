**To create a cache cluster**

The following ``create-cache-cluster`` example creates a cluster. All nodes in the cluster run the same protocol-compliant cache engine software, either Memcached or Redis. ::

    aws elasticache create-cache-cluster \
       --cache-cluster-id my-redis-cluster \
       --engine "redis" \
       --cache-node-type cache.m5.large \
       --num-cache-nodes 1

Output::

    {
        "CacheCluster": {
            "CacheClusterId": "my-memcached-cluster",
            "ClientDownloadLandingPage": "https://console.aws.amazon.com/elasticache/home#client-download:",
            "CacheNodeType": "cache.m5.large",
            "Engine": "redis",
            "EngineVersion": "5.0.5",
            "CacheClusterStatus": "creating",
            "NumCacheNodes": 1,
            "PreferredMaintenanceWindow": "sat:10:00-sat:11:00",
            "PendingModifiedValues": {},
            "CacheSecurityGroups": [],
            "CacheParameterGroup": {
                "CacheParameterGroupName": "default.redis5.0",
                "ParameterApplyStatus": "in-sync",
                "CacheNodeIdsToReboot": []
            },
            "CacheSubnetGroupName": "default",
            "AutoMinorVersionUpgrade": true,
            "SnapshotRetentionLimit": 0,
            "SnapshotWindow": "07:00-08:00",
            "TransitEncryptionEnabled": false,
            "AtRestEncryptionEnabled": false
        }
    }

For more information, see `Creating a Cluster <https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/Clusters.Create.html>`__ in the *Elasticache User Guide*.
