**Example 1: To describe scaling activities for the specified group**

This example describes the scaling activities for the specified Auto Scaling group. ::

    aws autoscaling describe-scaling-activities \
        --auto-scaling-group-name my-asg

Output::

    {
        "Activities": [
            {
                "ActivityId": "f9f2d65b-f1f2-43e7-b46d-d86756459699",
                "Description": "Launching a new EC2 instance: i-0d44425630326060f",
                "AutoScalingGroupName": "my-asg",
                "Cause": "At 2020-10-30T19:35:51Z a user request update of AutoScalingGroup constraints to min: 0, max: 16, desired: 16 changing the desired capacity from 0 to 16.  At 2020-10-30T19:36:07Z an instance was started in response to a difference between desired and actual capacity, increasing the capacity from 0 to 16.",
                "StartTime": "2020-10-30T19:36:09.766Z",
                "EndTime": "2020-10-30T19:36:41Z",
                "StatusCode": "Successful",
                "Progress": 100,
                "Details": "{\"Subnet ID\":\"subnet-5ea0c127\",\"Availability Zone\":\"us-west-2b\"}"
            }
        ]
    }

**Example 2: To describe the scaling activities of the specified activity ID**

To describe a specific scaling activity, use the ``--activity-ids`` option. ::

    aws autoscaling describe-scaling-activities \
        --activity-ids b55c7b67-c8aa-4d10-b240-730ff91d8895

Output::

    {
        "Activities": [
            {
                "ActivityId": "f9f2d65b-f1f2-43e7-b46d-d86756459699",
                "Description": "Launching a new EC2 instance: i-0d44425630326060f",
                "AutoScalingGroupName": "my-asg",
                "Cause": "At 2020-10-30T19:35:51Z a user request update of AutoScalingGroup constraints to min: 0, max: 16, desired: 16 changing the desired capacity from 0 to 16.  At 2020-10-30T19:36:07Z an instance was started in response to a difference between desired and actual capacity, increasing the capacity from 0 to 16.",
                "StartTime": "2020-10-30T19:36:09.766Z",
                "EndTime": "2020-10-30T19:36:41Z",
                "StatusCode": "Successful",
                "Progress": 100,
                "Details": "{\"Subnet ID\":\"subnet-5ea0c127\",\"Availability Zone\":\"us-west-2b\"}"
            }
        ]
    }

**Example 3: To describe a specified number of scaling activities**

To return a specific number of activities, use the ``--max-items`` option. ::

    aws autoscaling describe-scaling-activities --max-items 1

Output::

    {
        "Activities": [
            {
                "ActivityId": "f9f2d65b-f1f2-43e7-b46d-d86756459699",
                "Description": "Launching a new EC2 instance: i-0d44425630326060f",
                "AutoScalingGroupName": "my-asg",
                "Cause": "At 2020-10-30T19:35:51Z a user request update of AutoScalingGroup constraints to min: 0, max: 16, desired: 16 changing the desired capacity from 0 to 16.  At 2020-10-30T19:36:07Z an instance was started in response to a difference between desired and actual capacity, increasing the capacity from 0 to 16.",
                "StartTime": "2020-10-30T19:36:09.766Z",
                "EndTime": "2020-10-30T19:36:41Z",
                "StatusCode": "Successful",
                "Progress": 100,
                "Details": "{\"Subnet ID\":\"subnet-5ea0c127\",\"Availability Zone\":\"us-west-2b\"}"
            }
        ]
    }

If the output includes a ``NextToken`` field, there are more activities. To get the additional activities, use the value of this field with the ``--starting-token`` option in a subsequent call as follows. ::

    aws autoscaling describe-scaling-activities --starting-token Z3M3LMPEXAMPLE
