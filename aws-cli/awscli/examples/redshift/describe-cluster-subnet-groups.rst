**To get a description of all cluster subnet groups**

The following ``describe-cluster-subnet-groups`` example returns a description of all cluster subnet groups.  By default, the output is in JSON format. ::

    aws redshift describe-cluster-subnet-groups

Output::

    {
        "ClusterSubnetGroups": [
            {
                "Subnets": [
                    {
                        "SubnetStatus": "Active",
                        "SubnetIdentifier": "subnet-763fdd1c",
                        "SubnetAvailabilityZone": {
                            "Name": "us-west-2a"
                        }
                    }
                ],
                "VpcId": "vpc-7e3fdd14",
                "SubnetGroupStatus": "Complete",
                "Description": "My subnet group",
                "ClusterSubnetGroupName": "mysubnetgroup"
            }
        ]
    }

For more information, see `Subnets for Redshift resources <https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-cluster-subnet-groups.html>`__ in the *Amazon Redshift Management Guide*.
