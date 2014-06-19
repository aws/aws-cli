**To describe scheduled actions**

The following ``describe-scheduled-actions`` command returns all scheduled actions::

	aws autoscaling describe-scheduled-actions

The output of this command is a JSON block that describes the scheduled actions for all Auto Scaling groups, similar to the following::

	{
		"ScheduledUpdateGroupActions": [
			{
				"MinSize": 2,
				"DesiredCapacity": 4,
				"AutoScalingGroupName": "basic-auto-scaling-group",
				"MaxSize": 6,
				"Recurrence": "30 0 1 12 0",
				"ScheduledActionARN": "arn:aws:autoscaling:us-west-2:896650972448:scheduledUpdateGroupAction:8e86b655-b2e6-4410-8f29-b4f094d6871c:autoScalingGroupName/basic-auto-scaling-group:scheduledActionName/sample-scheduled-action",
				"ScheduledActionName": "sample-scheduled-action",
				"StartTime": "2019-12-01T00:30:00Z",
				"Time": "2019-12-01T00:30:00Z"
			}
		]
	}

To return the scheduled actions for a specific Auto Scaling group, use the ``auto-scaling-group-name`` parameter::

	aws autoscaling describe-scheduled-actions --auto-scaling-group-name basic-auto-scaling-group

To return a specific scheduled action, use the ``scheduled-action-names`` parameter::

	aws autoscaling describe-scheduled-actions --scheduled-action-names sample-scheduled-action

To return the scheduled actions that start at a specific time, use the ``start-time`` parameter::

	aws autoscaling describe-scheduled-actions --start-time "2019-12-01T00:30:00Z"

To return the scheduled actions that end at a specific time, use the ``end-time`` parameter::

	aws autoscaling describe-scheduled-actions --end-time "2022-12-01T00:30:00Z"

To return a specific number of scheduled actions with this command, use the ``max-items`` parameter::

	aws autoscaling describe-scheduled-actions --auto-scaling-group-name basic-auto-scaling-group --max-items 1

In this example, the output of this command is a JSON block that describes the first scheduled action::

	{
		"NextToken": "None___1",
		"NotificationConfigurations": [
			{
				"AutoScalingGroupName": "basic-auto-scaling-group",
				"NotificationType": "autoscaling:TEST_NOTIFICATION",
				"TopicARN": "arn:aws:sns:us-west-2:896650972448:second-test-topic"
			}
		]
	}

This JSON block includes a ``NextToken`` field. You can use the value of this field with the ``starting-token`` parameter to return scheduled actions::

    aws autoscaling describe-scheduled-actions --auto-scaling-group-name basic-auto-scaling-group --starting-token None___1

For more information, see `Scheduled Scaling`_ in the *Auto Scaling Developer Guide*.

.. _`Scheduled Scaling`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/schedule_time.html

