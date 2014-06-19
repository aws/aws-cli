**To terminate an instance in an Auto Scaling group**

The following ``terminate-instance-in-auto-scaling-group`` command terminates an instance from an Auto Scaling group without resetting the size of the group::

	aws autoscaling terminate-instance-in-auto-scaling-group --instance-id i-93633f9b --no-should-decrement-desired-capacity

This results in a new instance starting up after the specified instance terminates.

For more information, see `Configure Instance Termination Policy for Your Auto Scaling Group`_ in the *Auto Scaling Developer Guide*.

.. _`Configure Instance Termination Policy for Your Auto Scaling Group`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/us-termination-policy.html

