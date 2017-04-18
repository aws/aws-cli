**To launch an instance in EC2-Classic**

This example launches a single instance of type ``c3.large``.

The key pair and security group, named ``MyKeyPair`` and ``MySecurityGroup``, must exist.

Command::

  aws ec2 run-instances --image-id ami-1a2b3c4d --count 1 --instance-type c3.large --key-name MyKeyPair --security-groups MySecurityGroup

Output::

  {
      "OwnerId": "123456789012",
      "ReservationId": "r-08626e73c547023b1",
      "Groups": [
          {
              "GroupName": "MySecurityGroup",
              "GroupId": "sg-903004f8"
          }
      ],
      "Instances": [
          {
              "Monitoring": {
                  "State": "disabled"
              },
              "PublicDnsName": null,
              "RootDeviceType": "ebs",
              "State": {
                  "Code": 0,
                  "Name": "pending"
              },
              "EbsOptimized": false,
              "LaunchTime": "2013-07-19T02:42:39.000Z",
              "ProductCodes": [],
              "StateTransitionReason": null, 
              "InstanceId": "i-1234567890abcdef0",
              "ImageId": "ami-1a2b3c4d",
              "PrivateDnsName": null,
              "KeyName": "MyKeyPair",
              "SecurityGroups": [
                  {
                      "GroupName": "MySecurityGroup",
                      "GroupId": "sg-903004f8"
                  }
              ],
              "ClientToken": null,
              "InstanceType": "c3.large",
              "NetworkInterfaces": [],
              "Placement": {
                  "Tenancy": "default",
                  "GroupName": null,
                  "AvailabilityZone": "us-east-1b"
              },
              "Hypervisor": "xen",
              "BlockDeviceMappings": [],
              "Architecture": "x86_64",
              "StateReason": {
                  "Message": "pending",
                  "Code": "pending"
              },
              "RootDeviceName": "/dev/sda1",
              "VirtualizationType": "hvm",
              "AmiLaunchIndex": 0
          }
      ]
  }

**To launch an instance in EC2-VPC**

This example launches a single instance of type ``t2.micro`` into the specified subnet.

The key pair named ``MyKeyPair`` and the security group sg-903004f8 must exist.

Command::

  aws ec2 run-instances --image-id ami-abc12345 --count 1 --instance-type t2.micro --key-name MyKeyPair --security-group-ids sg-903004f8 --subnet-id subnet-6e7f829e

Output::

  {
      "OwnerId": "123456789012",
      "ReservationId": "r-08626e73c547023b2",
      "Groups": [],
      "Instances": [
          {
              "Monitoring": {
                  "State": "disabled"
              },
              "PublicDnsName": null,
              "RootDeviceType": "ebs",
              "State": {
                  "Code": 0,
                  "Name": "pending"
              },
              "EbsOptimized": false,
              "LaunchTime": "2013-07-19T02:42:39.000Z",
              "PrivateIpAddress": "10.0.1.114",
              "ProductCodes": [],
              "VpcId": "vpc-1a2b3c4d",
              "InstanceId": "i-1234567890abcdef5",
              "ImageId": "ami-abc12345",
              "PrivateDnsName": "ip-10-0-1-114.ec2.internal",
              "KeyName": "MyKeyPair",
              "SecurityGroups": [
                  {
                      "GroupName": "MySecurityGroup",
                      "GroupId": "sg-903004f8"
                  }
              ],
              "ClientToken": null,
              "SubnetId": "subnet-6e7f829e",
              "InstanceType": "t2.micro",
              "NetworkInterfaces": [
                  {
                      "Status": "in-use",
                      "MacAddress": "0e:ad:05:3b:60:52",
                      "SourceDestCheck": true,
                      "VpcId": "vpc-1a2b3c4d",
                      "Description": "null",
                      "NetworkInterfaceId": "eni-a7edb1c9",
                      "PrivateIpAddresses": [
                          {
                              "PrivateDnsName": "ip-10-0-1-114.ec2.internal",
                              "Primary": true,
                              "PrivateIpAddress": "10.0.1.114"
                          }
                      ],
                      "Ipv6Addresses": [],
                      "PrivateDnsName": "ip-10-0-1-114.ec2.internal",
                      "Attachment": {
                          "Status": "attached",
                          "DeviceIndex": 0,
                          "DeleteOnTermination": true,
                          "AttachmentId": "eni-attach-52193138",
                          "AttachTime": "2013-07-19T02:42:39.000Z"
                      },
                      "Groups": [
                          {
                              "GroupName": "MySecurityGroup",
                              "GroupId": "sg-903004f8"
                          }
                      ],
                      "SubnetId": "subnet-6e7f829e",
                      "OwnerId": "123456789012",
                      "PrivateIpAddress": "10.0.1.114"
                  }
              ],
              "SourceDestCheck": true,
              "Placement": {
                  "Tenancy": "default",
                  "GroupName": null,
                  "AvailabilityZone": "us-east-1b"
              },
              "Hypervisor": "xen",
              "BlockDeviceMappings": [],
              "Architecture": "x86_64",
              "StateReason": {
                  "Message": "pending",
                  "Code": "pending"
              },
              "RootDeviceName": "/dev/sda1",
              "VirtualizationType": "hvm",
              "AmiLaunchIndex": 0
          }
      ]
  }

The following example requests a public IP address for an instance that you're launching into a nondefault subnet:

Command::

  aws ec2 run-instances --image-id ami-c3b8d6aa --count 1 --instance-type t2.medium --key-name MyKeyPair --security-group-ids sg-903004f8 --subnet-id subnet-6e7f829e --associate-public-ip-address

**To launch an instance using a block device mapping**

Add the following parameter to your ``run-instances`` command to specify block devices::

  --block-device-mappings file://mapping.json

To add an Amazon EBS volume with the device name ``/dev/sdh`` and a volume size of 100, specify the following in mapping.json::

  [
    {
      "DeviceName": "/dev/sdh",
      "Ebs": {
        "VolumeSize": 100
      }
    }
  ]

To add ``ephemeral1`` as an instance store volume with the device name ``/dev/sdc``, specify the following in mapping.json::

  [
    {
      "DeviceName": "/dev/sdc",
      "VirtualName": "ephemeral1"
    }
  ]

To omit a device specified by the AMI used to launch the instance (for example, ``/dev/sdf``), specify the following in mapping.json::

  [
    {
      "DeviceName": "/dev/sdf",
      "NoDevice": ""
    }
  ]

You can view only the Amazon EBS volumes in your block device mapping using the console or the ``describe-instances`` command. To view all volumes, including the instance store volumes, use the following command.

Command::

  curl http://169.254.169.254/latest/meta-data/block-device-mapping/

Output::

  ami
  ephemeral1

Note that ``ami`` represents the root volume. To get details about the instance store volume ``ephemeral1``, use the following command.

Command::

  curl http://169.254.169.254/latest/meta-data/block-device-mapping/ephemeral1

Output::

  sdc

**To launch an instance with a modified block device mapping**

You can change individual characteristics of existing AMI block device mappings to suit your needs. Perhaps you want to use an existing AMI, but you want a larger root volume than the usual 8 GiB. Or, you would like to use a General Purpose (SSD) volume for an AMI that currently uses a Magnetic volume.

Use the ``describe-images`` command with the image ID of the AMI you want to use to find its existing block device mapping. You should see a block device mapping in the output::

  {
    "DeviceName": "/dev/sda1",
    "Ebs": {
      "DeleteOnTermination": true,
      "SnapshotId": "snap-1234567890abcdef0",
      "VolumeSize": 8,
      "VolumeType": "standard",
      "Encrypted": false
    }
  }

You can modify the above mapping by changing the individual parameters. For example, to launch an instance with a modified block device mapping, add the following parameter to your ``run-instances`` command to change the above mapping's volume size and type::

  --block-device-mappings file://mapping.json

Where mapping.json contains the following::

  [
    {
      "DeviceName": "/dev/sda1",
      "Ebs": {
        "DeleteOnTermination": true,
        "SnapshotId": "snap-1234567890abcdef0", 
        "VolumeSize": 100,
        "VolumeType": "gp2"
      }
    }
  ]

**To launch an instance with user data**

You can launch an instance and specify user data that performs instance configuration, or that runs a script. The user data needs to be passed as normal string, base64 encoding is handled internally. The following example passes user data in a file called ``my_script.txt`` that contains a configuration script for your instance. The script runs at launch.

Command::

  aws ec2 run-instances --image-id ami-abc1234 --count 1 --instance-type m4.large --key-name keypair --user-data file://my_script.txt --subnet-id subnet-abcd1234 --security-group-ids sg-abcd1234 

For more information about launching instances, see `Using Amazon EC2 Instances`_ in the *AWS Command Line Interface User Guide*.

.. _`Using Amazon EC2 Instances`: http://docs.aws.amazon.com/cli/latest/userguide/cli-ec2-launch.html

**To launch an instance with an instance profile**

This example shows the use of the ``iam-instance-profile`` option to specify an `IAM instance profile`_ by name.

.. _`IAM instance profile`: http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html

Command::

  aws ec2 run-instances --iam-instance-profile Name=MyInstanceProfile --image-id ami-1a2b3c4d --count 1 --instance-type t2.micro --key-name MyKeyPair --security-groups MySecurityGroup

**To launch an instance with tags**

You can launch an instance and specify tags for the instance, volumes, or both. The following example applies a tag with a key of ``webserver`` and value of ``production`` to the instance. The command also applies a tag with a key of ``cost-center`` and a value of ``cc123`` to any EBS volume that's created (in this case, the root volume).

Command::

  aws ec2 run-instances --image-id ami-abc12345 --count 1 --instance-type t2.micro --key-name MyKeyPair --subnet-id subnet-6e7f829e --tag-specifications 'ResourceType=instance,Tags=[{Key=webserver,Value=production}]' 'ResourceType=volume,Tags=[{Key=cost-center,Value=cc123}]' 