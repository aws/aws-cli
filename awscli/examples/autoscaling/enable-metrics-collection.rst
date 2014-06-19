**To enable metrics collection for an Auto Scaling group**

The following ``enable-metrics-collection`` command enables collecting data for an Auto Scaling group::

	aws autoscaling enable-metrics-collection --auto-scaling-group-name basic-auto-scaling-group --granularity "1Minute"

To collect data on a specific metric, use the ``metrics`` parameter::

	aws autoscaling enable-metrics-collection --auto-scaling-group-name basic-auto-scaling-group --metrics GroupDesiredCapacity --granularity "1Minute"

For more information, see `Monitoring Your Auto Scaling Instances`_ in the *Auto Scaling Developer Guide*.

.. _`Monitoring Your Auto Scaling Instances`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-instance-monitoring.html

