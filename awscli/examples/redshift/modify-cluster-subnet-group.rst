**To modify the subnets in a cluster subnet group**

The following ``modify-cluster-subnet-group`` example modifies the list of subnets in a cluster subnet group. By default, the output is in JSON format. ::

    aws redshift modify-cluster-subnet-group \
        --cluster-subnet-group-name mysubnetgroup \
        --subnet-ids subnet-763fdd1 subnet-ac830e9

Output::

    {
        "ClusterSubnetGroup":
        {
            "Subnets": [
                {
                    "SubnetStatus": "Active",
                    "SubnetIdentifier": "subnet-763fdd1c",
                    "SubnetAvailabilityZone":
                        { "Name": "us-east-1a" }
                },
                {
                    "SubnetStatus": "Active",
                    "SubnetIdentifier": "subnet-ac830e9",
                    "SubnetAvailabilityZone":
                        { "Name": "us-east-1b" }
                } ],
            "VpcId": "vpc-7e3fdd14",
            "SubnetGroupStatus": "Complete",
            "Description": "My subnet group",
            "ClusterSubnetGroupName": "mysubnetgroup"
        }
    }

