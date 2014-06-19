**To disable metrics collection for an Auto Scaling group**

The following ``disable-metrics-collection`` command disables collecting data for the ``GroupDesiredCapacity`` metric for an Auto Scaling group::

	aws autoscaling disable-metrics-collection --auto-scaling-group-name basic-auto-scaling-group --metrics GroupDesiredCapacity

For more information, see `Monitoring Your Auto Scaling Instances`_ in the *Auto Scaling Developer Guide*.

.. _`Monitoring Your Auto Scaling Instances`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-instance-monitoring.html

