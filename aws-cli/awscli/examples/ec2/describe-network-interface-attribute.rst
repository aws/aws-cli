**Example 1: To describe the attachment attribute of a network interface**

The following ``describe-network-interface-attribute`` example describes the ``attachment`` attribute of the specified network interface. ::

    aws ec2 describe-network-interface-attribute \
        --network-interface-id eni-686ea200 \
        --attribute attachment

Output::

    {
        "NetworkInterfaceId": "eni-686ea200",
        "Attachment": {
            "Status": "attached",
            "DeviceIndex": 0,
            "AttachTime": "2015-05-21T20:02:20.000Z",
            "InstanceId": "i-1234567890abcdef0",
            "DeleteOnTermination": true,
            "AttachmentId": "eni-attach-43348162",
            "InstanceOwnerId": "123456789012"
        }
    }

For more information, see `Modify network interface attributes <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/modify-network-interface-attributes.html>`__ in the *Amazon EC2 User Guide*.

**Example 2: To describe the description attribute of a network interface**

The following ``describe-network-interface-attribute`` example describes the ``description`` attribute of the specified network interface. ::

    aws ec2 describe-network-interface-attribute \
        --network-interface-id eni-686ea200 \
        --attribute description

Output::

    {
        "NetworkInterfaceId": "eni-686ea200",
        "Description": {
            "Value": "My description"
        }
    }

For more information, see `Modify network interface attributes <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/modify-network-interface-attributes.html>`__ in the *Amazon EC2 User Guide*.

**Example 3: To describe the groupSet attribute of a network interface**

The following ``describe-network-interface-attribute`` example describes the ``groupSet`` attribute of the specified network interface. ::

    aws ec2 describe-network-interface-attribute \
        --network-interface-id eni-686ea200 \
        --attribute groupSet

Output::

    {
        "NetworkInterfaceId": "eni-686ea200",
        "Groups": [
            {
                "GroupName": "my-security-group",
                "GroupId": "sg-903004f8"
            }
        ]
    }

For more information, see `Modify network interface attributes <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/modify-network-interface-attributes.html>`__ in the *Amazon EC2 User Guide*.

**Example 4: To describe the sourceDestCheck attribute of a network interface**

The following ``describe-network-interface-attribute`` example describes the ``sourceDestCheck`` attribute of the specified network interface. ::

    aws ec2 describe-network-interface-attribute \
        --network-interface-id eni-686ea200 \
        --attribute sourceDestCheck

Output::

    {
        "NetworkInterfaceId": "eni-686ea200",
        "SourceDestCheck": {
            "Value": true
        }
    }

For more information, see `Modify network interface attributes <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/modify-network-interface-attributes.html>`__ in the *Amazon EC2 User Guide*.
