**To move instances out of standby mode**

This example moves the specified instance out of standby mode::

    aws autoscaling exit-standby --instance-ids i-93633f9b --auto-scaling-group-name my-auto-scaling-group

The following is example output::

    {
        "Activities": [
            {
                "Description": "Moving EC2 instance out of Standby: i-93633f9b",
                "AutoScalingGroupName": "my-auto-scaling-group",
                "ActivityId": "142928e1-a2dc-453a-9b24-b85ad6735928",
                "Details": {"Availability Zone": "us-west-2a"},
                "StartTime": "2015-04-12T15:14:29.886Z",
                "Progress": 30,
                "Cause": "At 2015-04-12T15:14:29Z instance i-93633f9b was moved out of standby in response to a user request, increasing the capacity from 1 to 2.",
                "StatusCode": "PreInService"
            }
        ]
    }
