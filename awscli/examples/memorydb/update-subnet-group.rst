**To update a subnet group**

The following ``update-subnet-group`` example updates a subnet group's subnet ID. ::

    aws memorydb update-subnet-group \
        --subnet-group-name my-sg \
        --subnet-ids subnet-01f29d458f3xxxxx

Output::

    {
        "SubnetGroup": {
            "Name": "my-sg-1",
            "Description": "my-sg",
            "VpcId": "vpc-09d2cfc01xxxxxxx",
            "Subnets": [
                {
                    "Identifier": "subnet-01f29d458fxxxxxx",
                    "AvailabilityZone": {
                        "Name": "us-west-2a"
                    }
                }
            ],
            "ARN": "arn:aws:memorydb:us-west-2:491658xxxxxx:subnetgroup/my-sg"
        }
    }

For more information, see `Subnets and subnet groups <https://docs.aws.amazon.com/memorydb/latest/devguide/subnetgroups.html>`__ in the *MemoryDB User Guide*.
