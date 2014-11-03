**To describe the Auto Scaling adjustment types**

The following ``describe-adjustment types`` command describes the adjustment types available for Auto Scaling groups::

	aws autoscaling describe-adjustment-types

The output of this command is a JSON block that describes the adjustment types, similar to the following::

	{
		"AdjustementTypes": [
			{
				"AdjustmentType": "ChangeInCapacity"
			}
			{
				"AdjustmentType": "ExactCapcity"
			}
			{
				"AdjustmentType": "PercentChangeInCapacity"
			}
		]
	}

For more information, see `Dynamic Scaling`_ in the *Auto Scaling Developer Guide*.

.. _`Dynamic Scaling`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-scale-based-on-demand.html

