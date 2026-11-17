**To disable detailed monitoring for an instance**

The following ``unmonitor-instances`` example disables detailed monitoring for the specified instance. ::

    aws ec2 unmonitor-instances \
        --instance-ids i-1234567890abcdef0

Output::

    {
        "InstanceMonitorings": [
            {
                "InstanceId": "i-1234567890abcdef0",
                "Monitoring": {
                    "State": "disabling"
                }
            }
        ]
    }

For more information, see `Manage detailed monitoring for your EC2 instances <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/manage-detailed-monitoring.html>`__ in the *Amazon EC2 User Guide*.
