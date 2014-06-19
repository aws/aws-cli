**To execute an Auto Scaling policy**

The following ``execute-policy`` command executes an Auto Scaling policy for an Auto Scaling group::

	aws autoscaling execute-policy --auto-scaling-group-name basic-auto-scaling-group --policy-name ScaleIn --honor-cooldown

For more information, see `Dynamic Scaling`_ in the *Auto Scaling Developer Guide*.

.. _`Dynamic Scaling`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-scale-based-on-demand.html

