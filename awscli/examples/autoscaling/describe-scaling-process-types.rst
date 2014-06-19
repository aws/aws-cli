**To describe Auto Scaling process types**

The following ``describe-scaling-process-types`` command returns Auto Scaling process types::

	aws autoscaling describe-scaling-process-types

The output of this command is a JSON block that lists the processes, similar to the following::

	{
		"Processes": [
			{
				"ProcessName": "AZRebalance"
			},
			{
				"ProcessName": "AddToLoadBalancer"
			},
			{
				"ProcessName": "AlarmNotification"
			},
			{
				"ProcessName": "HealthCheck"
			},
			{
				"ProcessName": "Launch"
			},
			{
				"ProcessName": "ReplaceUnhealthy"
			},
			{
				"ProcessName": "ScheduledActions"
			},
			{
				"ProcessName": "Terminate"
			}
		]
	}

For more information, see `Suspend and Resume Auto Scaling Process`_ in the *Auto Scaling Developer Guide*.

.. _`Suspend and Resume Auto Scaling Process`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/US_SuspendResume.html

