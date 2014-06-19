**To describe the Auto Scaling notification types**

The following ``describe-auto-scaling-notification-types`` command describes the notification types available for Auto Scaling groups::

	aws autoscaling describe-auto-scaling-notification-types

The output of this command is a JSON block that describes the notification types, similar to the following::

	{
		"AutoScalingNotificationTypes": [
			"autoscaling:EC2_INSTANCE_LAUNCH",
			"autoscaling:EC2_INSTANCE_LAUNCH_ERROR",
			"autoscaling:EC2_INSTANCE_TERMINATE",
			"autoscaling:EC2_INSTANCE_TERMINATE_ERROR",
			"autoscaling:TEST_NOTIFICATION"
		]
	}

For more information, see the `Configure your Auto Scaling Group to Send Notifications`_ section in the Getting Notifications When Your Auto Scaling Group Changes topic, in the *Auto Scaling Developer Guide*.

.. _`Configure your Auto Scaling Group to Send Notifications`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/ASGettingNotifications.html#as-configure-asg-for-sns

