**To describe scheduled actions**

This example describes all your scheduled actions::

    aws autoscaling describe-scheduled-actions

The following is example output::

    {
        "ScheduledUpdateGroupActions": [
            {
                "MinSize": 2,
                "DesiredCapacity": 4,
                "AutoScalingGroupName": "my-auto-scaling-group",
                "MaxSize": 6,
                "Recurrence": "30 0 1 12 0",
                "ScheduledActionARN": "arn:aws:autoscaling:us-west-2:123456789012:scheduledUpdateGroupAction:8e86b655-b2e6-4410-8f29-b4f094d6871c:autoScalingGroupName/my-auto-scaling-group:scheduledActionName/my-scheduled-action",
                "ScheduledActionName": "my-scheduled-action",
                "StartTime": "2019-12-01T00:30:00Z",
                "Time": "2019-12-01T00:30:00Z"
            }
        ]
    }

To describe the scheduled actions for a specific Auto Scaling group, use the ``auto-scaling-group-name`` parameter::

    aws autoscaling describe-scheduled-actions --auto-scaling-group-name my-auto-scaling-group

To describe a specific scheduled action, use the ``scheduled-action-names`` parameter::

    aws autoscaling describe-scheduled-actions --scheduled-action-names my-scheduled-action

To describe the scheduled actions that start at a specific time, use the ``start-time`` parameter::

    aws autoscaling describe-scheduled-actions --start-time "2019-12-01T00:30:00Z"

To describe the scheduled actions that end at a specific time, use the ``end-time`` parameter::

    aws autoscaling describe-scheduled-actions --end-time "2022-12-01T00:30:00Z"

To return a specific number of scheduled actions, use the ``max-items`` parameter::

    aws autoscaling describe-scheduled-actions --auto-scaling-group-name my-auto-scaling-group --max-items 1

The following is example output::

    {
        "NextToken": "Z3M3LMPEXAMPLE",
        "ScheduledUpdateGroupActions": [
            {
                "MinSize": 2,
                "DesiredCapacity": 4,
                "AutoScalingGroupName": "my-auto-scaling-group",
                "MaxSize": 6,
                "Recurrence": "30 0 1 12 0",
                "ScheduledActionARN": "arn:aws:autoscaling:us-west-2:123456789012:scheduledUpdateGroupAction:8e86b655-b2e6-4410-8f29-b4f094d6871c:autoScalingGroupName/my-auto-scaling-group:scheduledActionName/my-scheduled-action",
                "ScheduledActionName": "my-scheduled-action",
                "StartTime": "2019-12-01T00:30:00Z",
                "Time": "2019-12-01T00:30:00Z"
            }
        ]
    }

Use the ``NextToken`` field with the ``starting-token`` parameter in a subsequent call to get the additional scheduled actions::

    aws autoscaling describe-scheduled-actions --auto-scaling-group-name my-auto-scaling-group --starting-token Z3M3LMPEXAMPLE

For more information, see `Scheduled Scaling`_ in the *Auto Scaling Developer Guide*.

.. _`Scheduled Scaling`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/schedule_time.html
