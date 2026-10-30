**Example 1: To create a placement group**

The following ``create-placement-group`` example creates a placement group with the specified name. ::

    aws ec2 create-placement-group \
        --group-name my-cluster \
        --strategy cluster

Output::

    {
        "PlacementGroup": {
            "GroupName": "my-cluster",
            "State": "available",
            "Strategy": "cluster",
            "GroupId": "pg-0123456789example",
            "GroupArn": "arn:aws:ec2:us-west-2:123456789012:placement-group/my-cluster"
        }
    }

**Example 2: To create a partition placement group**

The following ``create-placement-group`` example creates a partition placement group named ``HDFS-Group-A`` with five partitions. ::

    aws ec2 create-placement-group \
        --group-name HDFS-Group-A \
        --strategy partition \
        --partition-count 5

Output::

    {
        "PlacementGroup": {
            "GroupName": "HDFS-Group-A",
            "State": "available",
            "Strategy": "partition",
            "PartitionCount": 5,
            "GroupId": "pg-0abcdef1234example",
            "GroupArn": "arn:aws:ec2:us-west-2:123456789012:placement-group/HDFS-Group-A"
        }
    }
