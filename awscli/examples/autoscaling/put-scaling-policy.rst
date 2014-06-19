**To add a scaling policy to an Auto Scaling group**

The following ``put-scaling-policy`` command adds a policy to an Auto Scaling group::

	aws autoscaling put-scaling-policy --auto-scaling-group-name basic-auto-scaling-group --policy-name ScaleIn --scaling-adjustment -1 --adjustment-type ChangeInCapacity

To change the size of the auto scaling group by a specific number of instances, set the ``adjustment-type`` parameter to ``PercentChangeInCapacity``. Then, assign a value to
the ``min-adjustment-step`` parameter, where the value represents the number of instances you want the policy to add or remove from the Auto Scaling group::

	aws autoscaling put-scaling-policy --auto-scaling-group-name basic-auto-scaling-group --policy-name ScalePercentChange --scaling-adjustment 25 --adjustment-type PercentChangeInCapacity --cooldown 60 --min-adjustment-step 2

The output of the ``put-scaling-policy`` command is a JSON block that contains the arn of the policy::

	{
		"PolicyARN": "arn:aws:autoscaling:us-west-2:896650972448:scalingPolicy:2233f3d7-6290-403b-b632-93c553560106:autoScalingGroupName/basic-auto-scaling-group:policyName/ScaleIn"
	}

For more information, see `Dynamic Scaling`_ in the *Auto Scaling Developer Guide*.

.. _`Dynamic Scaling`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-scale-based-on-demand.html

