**To launch an Amazon EC2 instance**

The following ``run-instances`` command launches a single Amazon EC2 instance::

    aws ec2 run-instances --image-id ami-554ac83c count 1--key-name MyKeyPair --security-groups MySecurityGroup

The key pair and security group, named MyKeyPair and MySecurityGroup, must exist already.

The output of this command is a JSON block that describes the instance, similar to the following::

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
            "LaunchTime": "2012-12-19T02:42:39.000Z",
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
            "InstanceType": "m1.small",
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
            "RootDeviceType": "ebs",
            "AmiLaunchIndex": 0
        }
    ]

For more information, see `Launching an Amazon EC2 Instance`_ in the *AWS Command Line Interface User Guide*.

.. _Launching an Amazon EC2 Instance: http://docs.aws.amazon.com/cli/latest/userguide/cli-ec2-launch.html

