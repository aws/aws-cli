**Example 1: To describe an instance**

The following ``describe-instances`` example describes the specified instance. ::

    aws ec2 describe-instances \
        --instance-ids i-1234567890abcdef0

Output::

    {
       "Instances": [
            {
                "AmiLaunchIndex": 0,
                "ImageId": "ami-0abcdef1234567890,
                "InstanceId": "i-1234567890abcdef0,
                "InstanceType": "t2.micro",
                "KeyName": "MyKeyPair",
                "LaunchTime": "2018-05-10T08:05:20.000Z",
                "Monitoring": {
                    "State": "disabled"
                },
                "Placement": {
                    "AvailabilityZone": "us-east-2a",
                    "GroupName": "",
                    "Tenancy": "default"
                },
                "PrivateDnsName": "ip-10-0-0-157.us-east-2.compute.internal",
                "PrivateIpAddress": "10.0.0.157",
                "ProductCodes": [],
                "PublicDnsName": "",
                "State": {
                    "Code": 0,
                    "Name": "pending"
                },
                "StateTransitionReason": "",
                "SubnetId": "subnet-04a636d18e83cfacb",
                "VpcId": "vpc-1234567890abcdef0",
                "Architecture": "x86_64",
                "BlockDeviceMappings": [],
                "ClientToken": "",
                "EbsOptimized": false,
                "Hypervisor": "xen",
                "NetworkInterfaces": [
                    {
                        "Attachment": {
                            "AttachTime": "2018-05-10T08:05:20.000Z",
                            "AttachmentId": "eni-attach-0e325c07e928a0405",
                            "DeleteOnTermination": true,
                            "DeviceIndex": 0,
                            "Status": "attaching"
                        },
                        "Description": "",
                        "Groups": [
                            {
                                "GroupName": "MySecurityGroup",
                                "GroupId": "sg-0598c7d356eba48d7"
                            }
                        ],
                        "Ipv6Addresses": [],
                        "MacAddress": "0a:ab:58:e0:67:e2",
                        "NetworkInterfaceId": "eni-0c0a29997760baee7",
                        "OwnerId": "123456789012",
                        "PrivateDnsName": "ip-10-0-0-157.us-east-2.compute.internal",
                        "PrivateIpAddress": "10.0.0.157"
                        "PrivateIpAddresses": [
                            {
                                "Primary": true,
                                "PrivateDnsName": "ip-10-0-0-157.us-east-2.compute.internal",
                                "PrivateIpAddress": "10.0.0.157"
                            }
                        ],
                        "SourceDestCheck": true,
                        "Status": "in-use",
                        "SubnetId": "subnet-04a636d18e83cfacb",
                        "VpcId": "vpc-1234567890abcdef0",
                        "InterfaceType": "interface"
                    }
                ],
                "RootDeviceName": "/dev/xvda",
                "RootDeviceType": "ebs",
                "SecurityGroups": [
                    {
                        "GroupName": "MySecurityGroup",
                        "GroupId": "sg-0598c7d356eba48d7"
                    }
                ],
                "SourceDestCheck": true,
                "StateReason": {
                    "Code": "pending",
                    "Message": "pending"
                },
                "Tags": [],
                "VirtualizationType": "hvm",
                "CpuOptions": {
                    "CoreCount": 1,
                    "ThreadsPerCore": 1
                },
                "CapacityReservationSpecification": {
                    "CapacityReservationPreference": "open"
                },
                "MetadataOptions": {
                    "State": "pending",
                    "HttpTokens": "optional",
                    "HttpPutResponseHopLimit": 1,
                    "HttpEndpoint": "enabled"
                }
            }
        ],
        "OwnerId": "123456789012"
        "ReservationId": "r-02a3f596d91211712",
    }

**Example 2: To describe instances based on filters**

The following ``describe-instances`` example uses filters to scope the results to instances of the specified type. ::

    aws ec2 describe-instances \
        --filters Name=instance-type,Values=m5.large

The following ``describe-instances`` example uses multiple filters to scope the results to instances with the specified type that are also in the specified Availability Zone. ::

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

For an example of the output for ``describe-instances``, see Example 1.

**Example 3: To describe instances based on tags**

The following ``describe-instances`` example uses tag filters to scope the results to instances that have a tag with the specified tag key (Owner), regardless of the tag value. ::

    aws ec2 describe-instances \
        --filters "Name=tag-key,Values=Owner"

The following ``describe-instances`` example uses tag filters to scope the results to instances that have a tag with the specified tag value (my-team), regardless of the tag key. ::

    aws ec2 describe-instances \
        --filters "Name=tag-value,Values=my-team"

The following ``describe-instances`` example uses tag filters to scope the results to instances that have the specified tag (Owner=my-team). ::

    aws ec2 describe-instances \
        --filters "Name=tag:Owner,Values=my-team"

For an example of the output for ``describe-instances``, see Example 1.

**Example 4: To display only specific output**

The following ``describe-instances`` example uses the ``--query`` parameter to display only the instance and subnet IDs for all instances, in JSON format.

Linux command::

    aws ec2 describe-instances \
        --query 'Reservations[*].Instances[*].{Instance:InstanceId,Subnet:SubnetId}' \
        --output json

Windows command::

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
        ...
    ]

The following ``describe-instances`` example uses filters to scope the results to instances of the specified type and the ``--query`` parameter to display only the instance IDs. ::

    aws ec2 describe-instances \
        --filters Name=instance-type,Values=t2.micro \
        --query Reservations[*].Instances[*].[InstanceId] \
        --output text

Output::

    i-031c0dc19de2fb70c
    i-00d8bff789a736b75
    i-0b715c6b7db68927a
    i-0626d4edd54f1286d
    i-00b8ae04f9f99908e
    i-0fc71c25d2374130c

The following ``describe-instances`` example displays the instance ID, Availability Zone, and the value of the ``Name`` tag for instances that have a tag with the name ``tag-key``, in table format.

Linux command::

    aws ec2 describe-instances \
        --filters Name=tag-key,Values=Name \
        --query 'Reservations[*].Instances[*].{Instance:InstanceId,AZ:Placement.AvailabilityZone,Name:Tags[?Key==`Name`]|[0].Value}' \
        --output table

Windows command::

    aws ec2 describe-instances ^
        --filters Name=tag-key,Values=Name ^
        --query "Reservations[*].Instances[*].{Instance:InstanceId,AZ:Placement.AvailabilityZone,Name:Tags[?Key=='Name']|[0].Value}" ^
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

**Example 5: To describe instances in a partition placement group**

The following ``describe-instances`` example describes the specified instance. The output includes the placement information for the instance, which contains the placement group name and the partition number for the instance. ::

    aws ec2 describe-instances \
        --instance-id i-0123a456700123456

The following shows only the placement information from the output. ::

    "Placement": {
        "AvailabilityZone": "us-east-1c",
        "GroupName": "HDFS-Group-A",
        "PartitionNumber": 3,
        "Tenancy": "default"
    }

The following ``describe-instances`` example filters the results to only those instances with the specified placement group and partition number. ::

    aws ec2 describe-instances \
        --filters "Name = placement-group-name, Values = HDFS-Group-A" "Name = placement-partition-number, Values = 7"

The following shows only the relevant information from the output. ::

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

For more information, see `Describing instances in a placement group <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/placement-groups.html#describe-instance-placement>`__ in the *Amazon EC2 Users Guide*.
