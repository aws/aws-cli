**To create a replication instance**

The following ``create-replication-instance`` example creates a replication instance. ::

    aws dms create-replication-instance \
        --replication-instance-identifier my-repl-instance \
        --replication-instance-class dms.t2.micro \
        --allocated-storage 5

Output::

    {
        "ReplicationInstance": {
            "ReplicationInstanceIdentifier": "my-repl-instance",
            "ReplicationInstanceClass": "dms.t2.micro",
            "ReplicationInstanceStatus": "creating",
            "AllocatedStorage": 5,
            "VpcSecurityGroups": [
                {
                    "VpcSecurityGroupId": "sg-f839b688",
                    "Status": "active"
                }
            ],
            "ReplicationSubnetGroup": {
                "ReplicationSubnetGroupIdentifier": "default",
                "ReplicationSubnetGroupDescription": "default",
                "VpcId": "vpc-136a4c6a",
                "SubnetGroupStatus": "Complete",
                "Subnets": [
                    {
                        "SubnetIdentifier": "subnet-da327bf6",
                        "SubnetAvailabilityZone": {
                            "Name": "us-west-2a"
                        },
                        "SubnetStatus": "Active"
                    },
                    {
                        "SubnetIdentifier": "subnet-bac383e0",
                        "SubnetAvailabilityZone": {
                            "Name": "us-west-2c"
                        },
                        "SubnetStatus": "Active"
                    },
                    {
                        "SubnetIdentifier": "subnet-d7c825e8",
                        "SubnetAvailabilityZone": {
                            "Name": "us-west-2d"
                        },
                        "SubnetStatus": "Active"
                    },
                    {
                        "SubnetIdentifier": "subnet-cbfff283",
                        "SubnetAvailabilityZone": {
                            "Name": "us-west-2b"
                        },
                        "SubnetStatus": "Active"
                    }
                ]
            },
            "PreferredMaintenanceWindow": "sat:12:35-sat:13:05",
            "PendingModifiedValues": {},
            "MultiAZ": false,
            "EngineVersion": "3.3.2",
            "AutoMinorVersionUpgrade": true,
            "KmsKeyId": "arn:aws:kms:us-west-2:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "ReplicationInstanceArn": "arn:aws:dms:us-west-2:123456789012:rep:ZK2VQBUWFDBAWHIXHAYG5G2PKY",
            "PubliclyAccessible": true
        }
    }

For more information, see `Working with an AWS DMS Replication Instance <https://docs.aws.amazon.com/dms/latest/userguide/CHAP_ReplicationInstance.html>`__ in the *AWS Database Migration Service User Guide*.
