**Example 1: To describe the specified launch configuration**

The following ``describe-launch-configurations`` example describes the specified launch configuration. ::

    aws autoscaling describe-launch-configurations \
        --launch-configuration-names my-launch-config

Output::

    {
        "LaunchConfigurations": [
            {
                "LaunchConfigurationName": "my-launch-config",
                "LaunchConfigurationARN": "arn:aws:autoscaling:us-west-2:123456789012:launchConfiguration:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111:launchConfigurationName/my-launch-config",
                "ImageId": "ami-0528a5175983e7f28",
                "KeyName": "my-key-pair-uswest2",
                "SecurityGroups": [
                    "sg-05eaec502fcdadc2e"
                ],
                "ClassicLinkVPCSecurityGroups": [],
                "UserData": "",
                "InstanceType": "t2.micro",
                "KernelId": "",
                "RamdiskId": "",
                "BlockDeviceMappings": [
                    {
                        "DeviceName": "/dev/xvda",
                        "Ebs": {
                            "SnapshotId": "snap-06c1606ba5ca274b1",
                            "VolumeSize": 8,
                            "VolumeType": "gp2",
                            "DeleteOnTermination": true,
                            "Encrypted": false
                        }
                    }
                ],
                "InstanceMonitoring": {
                    "Enabled": true
                },
                "CreatedTime": "2020-10-28T02:39:22.321Z",
                "EbsOptimized": false,
                "AssociatePublicIpAddress": true,
                "MetadataOptions": {
                    "HttpTokens": "required",
                    "HttpPutResponseHopLimit": 1,
                    "HttpEndpoint": "disabled"
                }
            }
        ]
    }

**Example 2: To describe a specified number of launch configurations**

The following ``describe-launch-configurations`` example uses the ``--max-items`` option to return a specific number of launch configurations. ::

    aws autoscaling describe-launch-configurations \
        --max-items 1

Output::

    {
        "LaunchConfigurations": [
            {
                "LaunchConfigurationName": "my-launch-config",
                "LaunchConfigurationARN": "arn:aws:autoscaling:us-west-2:123456789012:launchConfiguration:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111:launchConfigurationName/my-launch-config",
                "ImageId": "ami-0528a5175983e7f28",
                "KeyName": "my-key-pair-uswest2",
                "SecurityGroups": [
                    "sg-05eaec502fcdadc2e"
                ],
                "ClassicLinkVPCSecurityGroups": [],
                "UserData": "",
                "InstanceType": "t2.micro",
                "KernelId": "",
                "RamdiskId": "",
                "BlockDeviceMappings": [
                    {
                        "DeviceName": "/dev/xvda",
                        "Ebs": {
                            "SnapshotId": "snap-06c1606ba5ca274b1",
                            "VolumeSize": 8,
                            "VolumeType": "gp2",
                            "DeleteOnTermination": true,
                            "Encrypted": false
                        }
                    }
                ],
                "InstanceMonitoring": {
                    "Enabled": true
                },
                "CreatedTime": "2020-10-28T02:39:22.321Z",
                "EbsOptimized": false,
                "AssociatePublicIpAddress": true,
                "MetadataOptions": {
                    "HttpTokens": "required",
                    "HttpPutResponseHopLimit": 1,
                    "HttpEndpoint": "disabled"
                }
            }
        ],
        "NextToken": "Z3M3LMPEXAMPLE"
    }

If the output includes a ``NextToken`` field, there are more launch configurations. To get the additional launch configurations, use the value of this field with the ``--starting-token`` option in a subsequent call as follows. ::

    aws autoscaling describe-launch-configurations \
        --starting-token Z3M3LMPEXAMPLE

For more information, see `Auto Scaling launch configurations <https://docs.aws.amazon.com/autoscaling/ec2/userguide/launch-configurations.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.
