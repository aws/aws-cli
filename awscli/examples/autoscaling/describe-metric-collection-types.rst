**To describe the Auto Scaling metric collection types**

The following ``describe-metric-collection-types`` command describes the metric collection types available for Auto Scaling groups::

	aws autoscaling describe-metric-collection-types

The output of this command is a JSON block that describes the metric collection types, similar to the following::

	{
		"Metrics": [
			{
				"Metric": "GroupMinSize"
			},
			{
				"Metric": "GroupMaxSize"
			},
			{
				"Metric": "GroupDesiredCapacity"
			},
			{
				"Metric": "GroupInServiceInstances"
			},
			{
				"Metric": "GroupPendingInstances"
			},
			{
				"Metric": "GroupTerminatingInstances"
			},
			{
				"Metric": "GroupTotalInstances"
			}
		],
		"Granularities": [
			{
				"Granularity": "1Minute"
			}
		]
	}

For more information, see the `Auto Scaling Group Metrics`_ section in the Monitoring Your Auto Scaling Instances topic, in the *Auto Scaling Developer Guide*.

.. _`Auto Scaling Group Metrics`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-instance-monitoring.html#as-group-metrics

