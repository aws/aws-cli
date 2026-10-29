**To launch a Scheduled Instance**

The following ``run-scheduled-instances`` example launches the specified Scheduled Instance in a VPC. ::

    aws ec2 run-scheduled-instances \
        --scheduled-instance-id sci-1234-1234-1234-1234-123456789012 \
        --instance-count 1 \
        --launch-specification file://launch-specification.json

Contents of ``launch-specification.json``::

    {
        "ImageId": "ami-12345678",
        "KeyName": "my-key-pair",
        "InstanceType": "c4.large",
        "NetworkInterfaces": [
            {
                "DeviceIndex": 0,
                "SubnetId": "subnet-12345678",
                "AssociatePublicIpAddress": true,
                "Groups": [
                    "sg-12345678"
                ]
            }
        ],
        "IamInstanceProfile": {
            "Name": "my-iam-role"
        }
    }

Output::

    {
        "InstanceIdSet": [
            "i-1234567890abcdef0"
        ]
    }

For more information, see `Amazon EC2 billing and purchasing options <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-purchasing-options.html>`__ in the *Amazon EC2 User Guide*.

The following ``run-scheduled-instances`` example launches the specified Scheduled Instance in EC2-Classic. ::

    aws ec2 run-scheduled-instances \
        --scheduled-instance-id sci-1234-1234-1234-1234-123456789012 \
        --instance-count 1 \
        --launch-specification file://launch-specification.json

Contents of ``launch-specification.json``::

    {
        "ImageId": "ami-12345678",
        "KeyName": "my-key-pair",
        "SecurityGroupIds": [
            "sg-12345678"
        ],
        "InstanceType": "c4.large",
        "Placement": {
            "AvailabilityZone": "us-west-2b"
        },
        "IamInstanceProfile": {
            "Name": "my-iam-role"
        }
    }

Output::

    {
        "InstanceIdSet": [
            "i-1234567890abcdef0"
        ]
    }

For more information, see `Amazon EC2 billing and purchasing options <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-purchasing-options.html>`__ in the *Amazon EC2 User Guide*.
