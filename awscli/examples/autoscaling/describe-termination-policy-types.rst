**To describe termination policy types**

The following ``describe-termination-policy-types`` command returns the available termination policy types::

	aws autoscaling describe-termination-policy-types

The output of this command is a JSON block that lists the types of termination policies, similar to the following::

	{
		"TerminationPolicyTypes": [
			"ClosestToNextInstanceHour",
			"Default",
			"NewestInstance",
			"OldestInstance",
			"OldestLaunchConfiguration"
		]
	}

For more information, see the `How Termination Policies Work`_ section in the Configure Instance Termination Policy for Your Auto Scaling Group topic, in the *Auto Scaling Developer Guide*.

.. _`How Termination Policies Work`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/us-termination-policy.html#your-termination-policy

