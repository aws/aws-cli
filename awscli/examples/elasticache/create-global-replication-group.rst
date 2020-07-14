**To create a global replication group**

The following ``create-global-replication-group`` example creates a new global replication group. ::

    aws elasticache create-global-replication-group \
        --global-replication-group-id-suffix my-global-replication-group \
        --primary-replication-group-id my-primary-cluster 

Output::

    {
        "CacheSubnetGroup": {
            "CacheSubnetGroupName": "my-global-replication-group",
            "CacheSubnetGroupDescription": "my subnet group",
            "VpcId": "vpc-xxxxxcdb",
            "Subnets": [
                {
                    "SubnetIdentifier": "subnet-xxxxexxf",
                    "SubnetAvailabilityZone": {
                        "Name": "us-west-2d"
                    }
                }
            ]
        }
    }

For more information, see `Replication Across AWS Regions Using Global Datastore <https://docs.amazonaws.cn/en_us/AmazonElastiCache/latest/red-ug/Redis-Global-Datastore.html>`__ in the *Elasticache User Guide*.
