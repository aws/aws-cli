**To start an Amazon EC2 instance**

The following ``start-instances`` command starts a single instance with the instance ID of ``i-1a2b3c4d``::

    aws ec2 start-instances --instance-ids i-1a2b3c4d

This command outputs a JSON block that contains descriptive information about the action, similar to the following::

    {
        "StartingInstances": [
            {
                "InstanceId": "i-1a2b3c4d",
                "CurrentState": {
                    "Code": 0,
                    "Name": "pending"
                },
                "PreviousState": {
                    "Code": 80,
                    "Name": "stopped"
                }
            }
        ],
        "ResponseMetadata": {
            "RequestId": "1fb7fb51-2f8f-40a4-b3f5-915d0bfbe735"
        }
    }

For more information, see `Stopping, Starting, and Terminating Instances`_ in the *EC2 User Guide*.

.. _Stopping, Starting, and Terminating Instances: http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-stopping-starting-terminating.html

