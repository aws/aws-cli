**To describe your Auto Scaling account limits**

The following ``describe-account-limits`` command describes your Auto Scaling account limits::

	aws autoscaling describe-account-limits

The output of this command is a JSON block that describes your Auto Scaling account limits, similar to the following::

	{
		"MaxNumberOfLaunchConfigurations": 100,
		"MaxNumberOfAutoScalingGroups": 20
	}

For more information, see `Auto Scaling Limits`_ in the *Auto Scaling Developer Guide*.

.. _`Auto Scaling Limits`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-account-limits.html

