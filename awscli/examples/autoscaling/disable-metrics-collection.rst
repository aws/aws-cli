**To disable metrics collection for an Auto Scaling group**

This example disables collecting data for the ``GroupDesiredCapacity`` metric for the specified Auto Scaling group::

    aws autoscaling disable-metrics-collection --auto-scaling-group-name my-auto-scaling-group --metrics GroupDesiredCapacity

For more information, see `Monitoring Your Auto Scaling Instances and Groups`_ in the *Auto Scaling Developer Guide*.

.. _`Monitoring Your Auto Scaling Instances and Groups`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-instance-monitoring.html
