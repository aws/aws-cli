**To describe an Amazon EC2 instance**

The following ``describe-instances`` example displays details about the specified instance. ::

    aws ec2 describe-instances \
        --instance-ids i-1234567890abcdef0

**To describe instances based on instance type**

The following ``describe-instances`` example displays details about all of your ``m5.large`` instances. ::

    aws ec2 describe-instances \
        --filters Name=instance-type,Values=m5.large

**To describe instances based on a tag key**

The following ``describe-instances`` example displays details about your instances that have a tag where the key name is ``Owner``. ::

    aws ec2 describe-instances \
        --filters "Name=tag-key,Values=Owner"

**To describe instances based on a tag**

The following ``describe-instances`` example displays details about instances with the tag ``Purpose=test``. ::

    aws ec2 describe-instances \
        --filters "Name=tag:Purpose,Values=test"

**To filter the results based on multiple conditions**

The following ``describe-instances`` example displays details about all instances with an instance type of ``t2.micro`` or ``t3.micro`` that are also in the ``us-east-2c`` Availability Zone. ::

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

**To filter the results to specific fields**

The following ``describe-instances`` example uses the ``--query`` parameter to display only its AMI ID and tags for the specified instance. ::

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

**To describe instances with a specific tag and filter the results to specific fields**

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
