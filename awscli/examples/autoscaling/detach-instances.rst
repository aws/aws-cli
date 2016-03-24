**To detach an instance from an Auto Scaling group**

This example detaches the specified instance from the specified Auto Scaling group::

    aws autoscaling detach-instances --instance-ids i-93633f9b --auto-scaling-group-name my-auto-scaling-group --should-decrement-desired-capacity

The following is example output::

    {
        "Activities": [
            {
                "Description": "Detaching EC2 instance: i-93633f9b",
                "AutoScalingGroupName": "my-auto-scaling-group",
                "ActivityId": "5091cb52-547a-47ce-a236-c9ccbc2cb2c9",
                "Details": {"Availability Zone": "us-west-2a"},
                "StartTime": "2015-04-12T15:02:16.179Z",
                "Progress": 50,
                "Cause": "At 2015-04-12T15:02:16Z instance i-93633f9b was detached in response to a user request, shrinking the capacity from 2 to 1.",
                "StatusCode": "InProgress"
            }
        ]
    }
