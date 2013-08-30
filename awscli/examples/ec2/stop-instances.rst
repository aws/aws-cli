**To stop an Amazon EC2 instance**

This example stops a running instance with the instance ID ``i-1a2b3c4d``.

Command::

  aws ec2 stop-instances --instance-ids i-1a2b3c4d

Output::

    {
        "StoppingInstances": [
            {
                "InstanceId": "i-1a2b3c4d",
                "CurrentState": {
                    "Code": 64,
                    "Name": "stopping"
                },
                "PreviousState": {
                    "Code": 16,
                    "Name": "running"
                }
            }
        ]
    }

For more information, see `Stop and Start Your Instance`_ in the *Amazon Elastic Compute Cloud User Guide*.

.. _`Stop and Start Your Instance`: http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Stop_Start.html

