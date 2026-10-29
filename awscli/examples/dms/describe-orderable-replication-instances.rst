**To describe orderable replication instances**

The following ``describe-orderable-replication-instances`` example lists replication instance types that you can order. ::

    aws dms describe-orderable-replication-instances

Output::

    {
        "OrderableReplicationInstances": [
            {
                "EngineVersion": "3.3.2",
                "ReplicationInstanceClass": "dms.c4.2xlarge",
                "StorageType": "gp2",
                "MinAllocatedStorage": 5,
                "MaxAllocatedStorage": 6144,
                "DefaultAllocatedStorage": 100,
                "IncludedAllocatedStorage": 100,
                "AvailabilityZones": [
                    "us-west-2a",
                    "us-west-2b",
                    "us-west-2c",
                    "us-west-2d"
                ]
            },
            {
                "EngineVersion": "3.3.2",
                "ReplicationInstanceClass": "dms.c4.4xlarge",
                "StorageType": "gp2",
                "MinAllocatedStorage": 5,
                "MaxAllocatedStorage": 6144,
                "DefaultAllocatedStorage": 100,
                "IncludedAllocatedStorage": 100,
                "AvailabilityZones": [
                    "us-west-2a",
                    "us-west-2b",
                    "us-west-2c",
                    "us-west-2d"
                ]
            }
        ]
    }

For more information, see `Working with an AWS DMS Replication Instance <https://docs.aws.amazon.com/dms/latest/userguide/CHAP_ReplicationInstance.html>`__ in the *AWS Database Migration Service User Guide*.
