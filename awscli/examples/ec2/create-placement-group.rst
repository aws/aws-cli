**Example 1: To create a placement group**

The following ``create-placement-group`` example creates a placement group with the specified name. ::

    aws ec2 create-placement-group \
        --group-name my-cluster \
        --strategy cluster

**Example 2: To create a partition placement group**

The following ``create-placement-group`` example creates a partition placement group named ``HDFS-Group-A`` with five partitions. ::

    aws ec2 create-placement-group \
        --group-name HDFS-Group-A \
        --strategy partition \
        --partition-count 5
