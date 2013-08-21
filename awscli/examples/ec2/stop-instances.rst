**To stop an Amazon EC2 instance**

The following ``stop-instances`` command stops a single running instance with the instance ID of ``i-1a2b3c4d``::

    aws ec2 stop-instances --instance-ids i-1a2b3c4d

This command outputs a JSON block that contains descriptive information about the action, similar to the following::

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
        ],
        "ResponseMetadata": {
            "RequestId": "1597c0de-ae8e-41d2-b773-940dfEXAMPLE"
        }
    }

For more information, see `Stopping, Starting, and Terminating Instances`_ in the *EC2 User Guide*.

.. _Stopping, Starting, and Terminating Instances: http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-stopping-starting-terminating.html

