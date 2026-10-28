**To enable detailed monitoring for an instance**

The following ``monitor-instances`` example enables detailed monitoring for the specified instance. ::

    aws ec2 monitor-instances --instance-ids i-1234567890abcdef0

Output::

    {
        "InstanceMonitorings": [
            {
                "InstanceId": "i-1234567890abcdef0",
                "Monitoring": {
                    "State": "pending"
                }
            }
        ]
    }
