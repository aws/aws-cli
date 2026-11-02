**Example 1: To describe the instance type**

The following ``describe-instance-attribute`` example describes the instance type of the specified instance. ::

    aws ec2 describe-instance-attribute \
        --instance-id i-1234567890abcdef0 \
        --attribute instanceType

Output::

    {
        "InstanceId": "i-1234567890abcdef0",
        "InstanceType": {
            "Value": "t1.micro"
        }
    }

For more information, see `Amazon EC2 instance type changes <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-resize.html>`__ in the *Amazon EC2 User Guide*.

**Example 2: To describe the disableApiTermination attribute**

The following ``describe-instance-attribute`` example describes the ``disableApiTermination`` attribute of the specified instance. ::

    aws ec2 describe-instance-attribute \
        --instance-id i-1234567890abcdef0 \
        --attribute disableApiTermination

Output::

    {
        "InstanceId": "i-1234567890abcdef0",
        "DisableApiTermination": {
            "Value": false
        }
    }

For more information, see `Change instance termination protection <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Using_ChangingDisableAPITermination.html>`__ in the *Amazon EC2 User Guide*.

**Example 3: To describe the block device mapping for an instance**

The following ``describe-instance-attribute`` example describes the ``blockDeviceMapping`` attribute of the specified instance. ::

    aws ec2 describe-instance-attribute \
        --instance-id i-1234567890abcdef0 \
        --attribute blockDeviceMapping

Output::

    {
        "InstanceId": "i-1234567890abcdef0",
        "BlockDeviceMappings": [
            {
                "DeviceName": "/dev/sda1",
                "Ebs": {
                    "Status": "attached",
                    "DeleteOnTermination": true,
                    "VolumeId": "vol-049df61146c4d7901",
                    "AttachTime": "2013-05-17T22:42:34.000Z"
                }
            },
            {
                "DeviceName": "/dev/sdf",
                "Ebs": {
                    "Status": "attached",
                    "DeleteOnTermination": false,
                    "VolumeId": "vol-049df61146c4d7901",
                    "AttachTime": "2013-09-10T23:07:00.000Z"
                }
            }
        ]
    }

For more information, see `Block device mappings for volumes on Amazon EC2 instances <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/block-device-mapping-concepts.html>`__ in the *Amazon EC2 User Guide*.
