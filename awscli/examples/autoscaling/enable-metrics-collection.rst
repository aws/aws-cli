**To enable metrics collection for an Auto Scaling group**

This example enables data collection for the specified Auto Scaling group::

    aws autoscaling enable-metrics-collection --auto-scaling-group-name my-auto-scaling-group --granularity "1Minute"

To collect data for a specific metric, use the ``metrics`` parameter::

    aws autoscaling enable-metrics-collection --auto-scaling-group-name my-auto-scaling-group --metrics GroupDesiredCapacity --granularity "1Minute"

For more information, see `Monitoring Your Auto Scaling Instances and Groups`_ in the *Auto Scaling Developer Guide*.

.. _`Monitoring Your Auto Scaling Instances and Groups`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-instance-monitoring.html
