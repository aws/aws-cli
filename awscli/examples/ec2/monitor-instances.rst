**To enable detailed monitoring for an instance**

This example command enables detailed monitoring for the specified instance.

Command::

  aws ec2 monitor-instances --instance-ids i-570e5a28

Output::

  {
    "InstanceMonitorings": [
        {
            "InstanceId": "i-570e5a28",
            "Monitoring": {
                "State": "pending"
            }
        }
    ]
  }
