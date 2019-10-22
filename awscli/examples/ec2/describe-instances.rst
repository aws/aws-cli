**Example 1: To describe an Amazon EC2 instance**

The following ``describe-instances`` example displays details about the specified instance. ::

    aws ec2 describe-instances \
        --instance-ids i-1234567890abcdef0

**Example 2: To describe instances based on instance type**

The following ``describe-instances`` example displays details about only instances of the specified type. ::

    aws ec2 describe-instances \
        --filters Name=instance-type,Values=m5.large

**Example 3: To describe instances based on a tag key and value**

The following ``describe-instances`` example displays details about only those instances that have a tag with the specified key name and value. ::

    aws ec2 describe-instances \
        --filters "Name=tag-key,Values=Owner"

**Example 4: To filter the results based on multiple conditions**

The following ``describe-instances`` example displays details about all instances with the specified type that are also in the specified Availability Zone. ::

    aws ec2 describe-instances \
        --filters Name=instance-type,Values=t2.micro,t3.micro Name=availability-zone,Values=us-east-2c

The following ``describe-instances`` example uses a JSON input file to perform the same filtering as the previous example. When filters get more complicated, they can be easier to specify in a JSON file. ::

    aws ec2 describe-instances \
        --filters file://filters.json

Contents of ``filters.json``::

    [
        {
            "Name": "instance-type",
            "Values": ["t2.micro", "t3.micro"]
        },
        {
            "Name": "availability-zone",
            "Values": ["us-east-2c"]
        }
    ]

**Example 5: To restrict the results to only specified fields**

The following ``describe-instances`` example uses the ``--query`` parameter to display only the AMI ID and tags for the specified instance. ::

    aws ec2 describe-instances \
        --instance-id i-1234567890abcdef0 \
        --query "Reservations[*].Instances[*].[ImageId,Tags[*]]"

The following ``describe-instances`` example uses the ``--query`` parameter to display only the instance and subnet IDs for all instances.

Linux Command::

    aws ec2 describe-instances \
        --query 'Reservations[*].Instances[*].{Instance:InstanceId,Subnet:SubnetId}' \
        --output json

Windows Command::

    aws ec2 describe-instances ^
        --query "Reservations[*].Instances[*].{Instance:InstanceId,Subnet:SubnetId}" ^
        --output json

Output::

    [
        {
            "Instance": "i-057750d42936e468a",
            "Subnet": "subnet-069beee9b12030077"
        },
        {
            "Instance": "i-001efd250faaa6ffa",
            "Subnet": "subnet-0b715c6b7db68927a"
        },
        {
            "Instance": "i-027552a73f021f3bd",
            "Subnet": "subnet-0250c25a1f4e15235"
        }
    ]

**Example 6: To describe instances with a specific tag and filter the results to specific fields**

The following ``describe-instances`` example displays the instance ID, Availability Zone, and the value of the ``Name`` tag for instances that have a tag with the name ``tag-key``.

Linux Command::

    aws ec2 describe-instances \
        --filter Name=tag-key,Values=Name \
        --query 'Reservations[*].Instances[*].{Instance:InstanceId,AZ:Placement.AvailabilityZone,Name:Tags[?Key==`Name`]|[0].Value}' \
        --output table

Windows Command::

    aws ec2 describe-instances ^
        --filter Name=tag-key,Values=Name ^
        --query "Reservations[*].Instances[*].{Instance:InstanceId,AZ:Placement.AvailabilityZone,Name:Tags[?Key==`Name`]|[0].Value}" ^
        --output table

Output::

  -------------------------------------------------------------
  |                     DescribeInstances                     |
  +--------------+-----------------------+--------------------+
  |      AZ      |       Instance        |        Name        |
  +--------------+-----------------------+--------------------+
  |  us-east-2b  |  i-057750d42936e468a  |  my-prod-server    |
  |  us-east-2a  |  i-001efd250faaa6ffa  |  test-server-1     |
  |  us-east-2a  |  i-027552a73f021f3bd  |  test-server-2     |
  +--------------+-----------------------+--------------------+

**Example 7: To view the partition number for an instance in a partition placement group**

The following ``describe-instances`` example displays details about the specified instance. The output includes the placement information for the instance, which contains the placement group name and the partition number for the instance. ::

    aws ec2 describe-instances \
        --instance-id i-0123a456700123456

The following output is truncated to show only the relevant information::

    "Placement": {
        "AvailabilityZone": "us-east-1c",
        "GroupName": "HDFS-Group-A",
        "PartitionNumber": 3,
        "Tenancy": "default"
    }

For more information, see `Describing Instances in a Placement Group <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/placement-groups.html#describe-instance-placement>`__ in the *Amazon Elastic Compute Cloud Users Guide*.

**Example 8: To filter instances for a specific partition placement group and partition number**

The following ``describe-instances`` example filters the results to only those instances with the specified placement group and partition number. ::

    aws ec2 describe-instances \
        --filters "Name = placement-group-name, Values = HDFS-Group-A" "Name = placement-partition-number, Values = 7"

The following output is truncated to show only the relevant pieces::

    "Instances": [
        {   
            "InstanceId": "i-0123a456700123456",
            "InstanceType": "r4.large",
            "Placement": {
                "AvailabilityZone": "us-east-1c",
                "GroupName": "HDFS-Group-A",
                "PartitionNumber": 7,
                "Tenancy": "default"
            }
        },
        {   
            "InstanceId": "i-9876a543210987654",
            "InstanceType": "r4.large",
            "Placement": {
                "AvailabilityZone": "us-east-1c",
                "GroupName": "HDFS-Group-A",
                "PartitionNumber": 7,
                "Tenancy": "default"
            }
        ],

For more information, see `Describing Instances in a Placement Group <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/placement-groups.html#describe-instance-placement>`__ in the *Amazon Elastic Compute Cloud Users Guide*.
