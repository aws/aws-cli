**To terminate an Amazon EC2 instance**

The following ``terminate-instances`` example terminates the specified instance. ::

    aws ec2 terminate-instances \
        --instance-ids i-1234567890abcdef0

Output::

    {
        "TerminatingInstances": [
            {
                "InstanceId": "i-1234567890abcdef0",
                "CurrentState": {
                    "Code": 32,
                    "Name": "shutting-down"
                },
                "PreviousState": {
                    "Code": 16,
                    "Name": "running"
                }
            }
        ]
    }

For more information, see `Launching, listing, and deleting Amazon EC2 instances in the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-services-ec2-instances.html>`__ in the *AWS Command Line Interface User Guide*.
