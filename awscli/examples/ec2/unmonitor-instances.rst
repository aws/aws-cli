**To disable detailed monitoring for an instance**

This example command disables detailed monitoring for the specified instance.

Command::

  aws ec2 unmonitor-instances --instance-ids i-570e5a28

Output::

  {
    "InstanceMonitorings": [
        {
            "InstanceId": "i-570e5a28",
            "Monitoring": {
                "State": "disabling"
            }
        }
    ]
  }
