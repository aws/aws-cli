**To get a description of the scaling activities for an Auto Scaling group**

This example describes the scaling activities for the specified Auto Scaling group::

    aws autoscaling describe-scaling-activities --auto-scaling-group-name my-auto-scaling-group

The following is example output::

    {
        "Activities": [
            {
                "Description": "Launching a new EC2 instance: i-4ba0837f",
                "AutoScalingGroupName": "my-auto-scaling-group",
                "ActivityId": "f9f2d65b-f1f2-43e7-b46d-d86756459699",
                "Details": "{"Availability Zone":"us-west-2c"}",
                "StartTime": "2013-08-19T20:53:29.930Z",
                "Progress": 100,
                "EndTime": "2013-08-19T20:54:02Z",
                "Cause": "At 2013-08-19T20:53:25Z a user request created an AutoScalingGroup changing the desired capacity from 0 to 1.  At 2013-08-19T20:53:29Z an instance was started in response to a difference between desired and actual capa city, increasing the capacity from 0 to 1.",
                "StatusCode": "Successful"
            }
        ]
    }

To describe a specific scaling activity, use the ``activity-ids`` parameter::

    aws autoscaling describe-scaling-activities --activity-ids b55c7b67-c8aa-4d10-b240-730ff91d8895

To return a specific number of activities, use the ``max-items`` parameter::

    aws autoscaling describe-scaling-activities --max-items 1

If the output includes a ``NextToken`` field, there are more activities. To get the additional activities, use the value of this field with the ``starting-token`` parameter in a subsequent call as follows::

    aws autoscaling describe-scaling-activities --starting-token Z3M3LMPEXAMPLE
