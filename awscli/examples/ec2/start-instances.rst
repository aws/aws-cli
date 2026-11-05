**To start an Amazon EC2 instance**

The following ``start-instances`` example starts the specified Amazon EBS-backed instance. ::

    aws ec2 start-instances \
        --instance-ids i-1234567890abcdef0

Output::

    {
        "StartingInstances": [
            {
                "InstanceId": "i-1234567890abcdef0",
                "CurrentState": {
                    "Code": 0,
                    "Name": "pending"
                },
                "PreviousState": {
                    "Code": 80,
                    "Name": "stopped"
                }
            }
        ]
    }

For more information, see `Stop and start Amazon EC2 instances <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Stop_Start.html>`__ in the *Amazon EC2 User Guide*.
