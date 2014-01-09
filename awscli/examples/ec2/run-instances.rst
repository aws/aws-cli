**To launch an instance in EC2-Classic**

This example launches a single instance of type ``t1.micro``.

The key pair and security group, named ``MyKeyPair`` and ``MySecurityGroup``, must exist.

Command::

  aws ec2 run-instances --image-id ami-c3b8d6aa --count 1 --instance-type t1.micro --key-name MyKeyPair --security-groups MySecurityGroup

Output::

  {
      "OwnerId": "123456789012",
      "ReservationId": "r-5875ca20",
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
              "Platform": "windows",
              "State": {
                  "Code": 0,
                  "Name": "pending"
              },
              "EbsOptimized": false,
              "LaunchTime": "2013-07-19T02:42:39.000Z",
              "ProductCodes": [],
              "InstanceId": "i-5203422c",
              "ImageId": "ami-c3b8d6aa",
              "PrivateDnsName": null,
              "KeyName": "MyKeyPair",
              "SecurityGroups": [
                  {
                      "GroupName": "MySecurityGroup",
                      "GroupId": "sg-903004f8"
                  }
              ],
              "ClientToken": null,
              "InstanceType": "t1.micro",
              "NetworkInterfaces": [],
              "Placement": {
                  "Tenancy": "default",
                  "GroupName": null,
                  "AvailabilityZone": "us-east-1b"
              },
              "Hypervisor": "xen",
              "BlockDeviceMappings": [
                  {
                      "DeviceName": "/dev/sda1",
                      "Ebs": {
                          "Status": "attached",
                          "DeleteOnTermination": true,
                          "VolumeId": "vol-877166c8",
                          "AttachTime": "2013-07-19T02:42:39.000Z"
                      }
                  }              
              ],
              "Architecture": "x86_64",
              "StateReason": {
                  "Message": "pending",
                  "Code": "pending"
              },
              "RootDeviceName": "/dev/sda1",
              "VirtualizationType": "hvm",
              "RootDeviceType": "ebs",
              "Tags": [
                  {
                      "Value": "MyInstance",
                      "Key": "Name"
                  }
              ],
              "AmiLaunchIndex": 0
          }
      ]
  }

**To launch an instance in EC2-VPC**

This example launches a single instance of type ``t1.micro`` into the specified subnet.

The key pair named ``MyKeyPair`` and the security group sg-903004f8 must exist.

Command::

  aws ec2 run-instances --image-id ami-c3b8d6aa --count 1 --instance-type t1.micro --key-name MyKeyPair --security-group-ids sg-903004f8 --subnet-id subnet-6e7f829e

Output::

  {
      "OwnerId": "123456789012",
      "ReservationId": "r-5875ca20",
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
              "Platform": "windows",
              "State": {
                  "Code": 0,
                  "Name": "pending"
              },
              "EbsOptimized": false,
              "LaunchTime": "2013-07-19T02:42:39.000Z",
              "PrivateIpAddress": "10.0.1.114",
              "ProductCodes": [],
              "VpcId": "vpc-1a2b3c4d",
              "InstanceId": "i-5203422c",
              "ImageId": "ami-c3b8d6aa",
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
              "InstanceType": "t1.micro",
              "NetworkInterfaces": [
                  {
                      "Status": "in-use",
                      "SourceDestCheck": true,
                      "VpcId": "vpc-1a2b3c4d",
                      "Description": "Primary network interface",
                      "NetworkInterfaceId": "eni-a7edb1c9",
                      "PrivateIpAddresses": [
                          {
                              "PrivateDnsName": "ip-10-0-1-114.ec2.internal",
                              "Primary": true,
                              "PrivateIpAddress": "10.0.1.114"
                          }
                      ],
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
              "BlockDeviceMappings": [
                  {
                      "DeviceName": "/dev/sda1",
                      "Ebs": {
                          "Status": "attached",
                          "DeleteOnTermination": true,
                          "VolumeId": "vol-877166c8",
                          "AttachTime": "2013-07-19T02:42:39.000Z"
                      }
                  }              
              ],
              "Architecture": "x86_64",
              "StateReason": {
                  "Message": "pending",
                  "Code": "pending"
              },
              "RootDeviceName": "/dev/sda1",
              "VirtualizationType": "hvm",
              "RootDeviceType": "ebs",
              "Tags": [
                  {
                      "Value": "MyInstance",
                      "Key": "Name"
                  }
              ],
              "AmiLaunchIndex": 0
          }
      ]
  }

For more information, see `Using Amazon EC2 Instances`_ in the *AWS Command Line Interface User Guide*.

.. _`Using Amazon EC2 Instances`: http://docs.aws.amazon.com/cli/latest/userguide/cli-ec2-launch.html

