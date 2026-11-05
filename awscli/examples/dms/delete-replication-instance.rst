**To delete a replication instance**

The following ``delete-replication-instance`` example deletes a replication instance. ::

    aws dms delete-replication-instance \
        --replication-instance-arn arn:aws:dms:us-west-2:123456789012:rep:T3OM7OUB5NM2LCVZF7JPGJRNUE

Output::

    {
        "ReplicationInstance": {
            "ReplicationInstanceIdentifier": "my-repl-instance",
            "ReplicationInstanceClass": "dms.t2.micro",
            "ReplicationInstanceStatus": "deleting",
            "AllocatedStorage": 5,
            "InstanceCreateTime": 1590011235.952,
            "VpcSecurityGroups": [
                {
                    "VpcSecurityGroupId": "sg-f839b688",
                    "Status": "active"
                }
            ],
            "AvailabilityZone": "us-west-2d",
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
            "PreferredMaintenanceWindow": "wed:11:42-wed:12:12",
            "PendingModifiedValues": {},
            "MultiAZ": true,
            "EngineVersion": "3.3.2",
            "AutoMinorVersionUpgrade": true,
            "KmsKeyId": "arn:aws:kms:us-west-2:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "ReplicationInstanceArn": "arn:aws:dms:us-west-2:123456789012:rep:T3OM7OUB5NM2LCVZF7JPGJRNUE",
            "ReplicationInstancePublicIpAddress": "54.225.120.92",
            "ReplicationInstancePrivateIpAddress": "172.31.30.121",
            "ReplicationInstancePublicIpAddresses": [
                "54.225.120.92",
                "3.230.18.248"
            ],
            "ReplicationInstancePrivateIpAddresses": [
                "172.31.30.121",
                "172.31.75.90"
            ],
            "PubliclyAccessible": true,
            "SecondaryAvailabilityZone": "us-west-2b"
        }
    }

For more information, see `Working with an AWS DMS Replication Instance <https://docs.aws.amazon.com/dms/latest/userguide/CHAP_ReplicationInstance.html>`__ in the *AWS Database Migration Service User Guide*.
