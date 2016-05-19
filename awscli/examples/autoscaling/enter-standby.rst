**To move instances into standby mode**

This example puts the specified instance into standby mode::

    aws autoscaling enter-standby --instance-ids i-93633f9b --auto-scaling-group-name my-auto-scaling-group --should-decrement-desired-capacity

The following is example output::

    {
        "Activities": [
            {
                "Description": "Moving EC2 instance to Standby: i-93633f9b",
                "AutoScalingGroupName": "my-auto-scaling-group",
                "ActivityId": "ffa056b4-6ed3-41ba-ae7c-249dfae6eba1",
                "Details": {"Availability Zone": "us-west-2a"},
                "StartTime": "2015-04-12T15:10:23.640Z",
                "Progress": 50,
                "Cause": "At 2015-04-12T15:10:23Z instance i-93633f9b was moved to standby in response to a user request, shrinking the capacity from 2 to 1.",
                "StatusCode": "InProgress"
            }
        ]
    }
