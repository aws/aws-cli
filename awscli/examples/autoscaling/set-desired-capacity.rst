**To set the desired capacity for an Auto Scaling group**

The following ``set-desired-capacity`` command sets the desired capacity for an Auto Scaling group::

	aws autoscaling set-desired-capacity --auto-scaling-group-name basic-auto-scaling-group --desired-capacity 2 --honor-cooldown

For more information, see `How Auto Scaling Works`_ in the *Auto Scaling Developer Guide*.

.. _`How Auto Scaling Works`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/how-as-works.html

