**To create a cluster subnet group**

The following ``create-cluster-subnet-group`` example creates a new cluster subnet group. ::

    aws redshift create-cluster-subnet-group \
        --cluster-subnet-group-name mysubnetgroup \
        --description "My subnet group" \
        --subnet-ids subnet-763fdd1c

Output::

    {
        "ClusterSubnetGroup": {
            "Subnets": [
                {
                    "SubnetStatus": "Active",
                    "SubnetIdentifier": "subnet-763fdd1c",
                    "SubnetAvailabilityZone": {
                        "Name": "us-east-1a"
                    }
                } ],
            "VpcId": "vpc-7e3fdd14",
            "SubnetGroupStatus": "Complete",
            "Description": "My subnet group",
            "ClusterSubnetGroupName": "mysubnetgroup"
        }
    }


