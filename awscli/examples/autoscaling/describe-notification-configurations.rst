**To describe the Auto Scaling notification configurations**

The following ``describe-notification-configurations`` command returns the notification configurations for an Auto Scaling group::

	aws autoscaling describe-notification-configurations --auto-scaling-group-name basic-auto-scaling-group

The output of this command is a JSON block that describes the notification configurations, similar to the following::

	{
		"NotificationConfigurations": [
			{
				"AutoScalingGroupName": "basic-auto-scaling-group",
				"NotificationType": "autoscaling:TEST_NOTIFICATION",
				"TopicARN": "arn:aws:sns:us-west-2:896650972448:second-test-topic"
			},
			{
				"AutoScalingGroupName": "basic-auto-scaling-group",
				"NotificationType": "autoscaling:TEST_NOTIFICATION",
				"TopicARN": "arn:aws:sns:us-west-2:896650972448:test-topic"
			}
		]
	}

To return a specific number of notification configurations with this command, use the ``max-items`` parameter::

	aws autoscaling describe-notification-configurations --auto-scaling-group-name basic-auto-scaling-group --max-items 1

In this example, the output of this command is a JSON block that describes the first notification configuration::

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

This JSON block includes a ``NextToken`` field. You can use the value of this field with the ``starting-token`` parameter to return additional notification configurations::

    aws autoscaling describe-notification-configurations --auto-scaling-group-name basic-auto-scaling-group --starting-token None___1

For more information, see `Getting Notifications When Your Auto Scaling Group Changes`_ in the *Auto Scaling Developer Guide*.

.. _`Getting Notifications When Your Auto Scaling Group Changes`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/ASGettingNotifications.html

