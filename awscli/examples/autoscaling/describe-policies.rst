**To describe Auto Scaling policies**

The following ``describe-policies`` command returns the policies for an Auto Scaling group::

	aws autoscaling describe-policies --auto-scaling-group-name basic-auto-scaling-group

The output of this command is a JSON block that describes the notification configurations, similar to the following::

	{
		"ScalingPolicies": [
			{
				"PolicyName": "ScaleIn",
				"AutoScalingGroupName": "basic-auto-scaling-group",
				"PolicyARN": "arn:aws:autoscaling:us-west-2:896650972448:scalingPolicy:2233f3d7-6290-403b-b632-93c553560106:autoScalingGroupName/basic-auto-scaling-group:policyName/ScaleIn",
				"AdjustmentType": "ChangeInCapacity",
				"Alarms": [],
				"ScalingAdjustment": -1
			},
			{
				"PolicyName": "ScalePercentChange",
				"MinAdjustmentStep": 2,
				"AutoScalingGroupName": "basic-auto-scaling-group",
				"PolicyARN": "arn:aws:autoscaling:us-west-2:896650972448:scalingPolicy:2b435159-cf77-4e89-8c0e-d63b497baad7:autoScalingGroupName/basic-auto-scaling-group:policyName/ScalePercentChange",
				"Cooldown": 60,
				"AdjustmentType": "PercentChangeInCapacity",
				"Alarms": [],
				"ScalingAdjustment": 25
			}
		]
	}

To return specific scaling policies with this command, use the ``policy-names`` parameter::

	aws autoscaling describe-policies --auto-scaling-group-name basic-auto-scaling-group --policy-names ScaleIn

To return a specific number of policies with this command, use the ``max-items`` parameter::

	aws autoscaling describe-policies --auto-scaling-group-name basic-auto-scaling-group --max-items 1

In this example, the output of this command is a JSON block that describes the first policy::

	{
		"ScalingPolicies": [
			{
				"PolicyName": "ScaleIn",
				"AutoScalingGroupName": "basic-auto-scaling-group",
				"PolicyARN": "arn:aws:autoscaling:us-west-2:896650972448:scalingPolicy:2233f3d7-6290-403b-b632-93c553560106:autoScalingGroupName/basic-auto-scaling-group:policyName/ScaleIn",
				"AdjustmentType": "ChangeInCapacity",
				"Alarms": [],
				"ScalingAdjustment": -1
			}
		],
		"NextToken": "None___1"
	}

This JSON block includes a ``NextToken`` field. You can use the value of this field with the ``starting-token`` parameter to return additional policies::

    aws autoscaling describe-policies --auto-scaling-group-name basic-auto-scaling-group --starting-token None___1

For more information, see `Dynamic Scaling`_ in the *Auto Scaling Developer Guide*.

.. _`Dynamic Scaling`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-scale-based-on-demand.html

