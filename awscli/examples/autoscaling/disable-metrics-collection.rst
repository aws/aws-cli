**To disable metrics collection for an Auto Scaling group**

This example disables collecting data for the ``GroupDesiredCapacity`` metric for the specified Auto Scaling group::

    aws autoscaling disable-metrics-collection --auto-scaling-group-name my-auto-scaling-group --metrics GroupDesiredCapacity

For more information, see `Monitoring Your Auto Scaling Groups and Instances Using Amazon CloudWatch`_ in the *Amazon EC2 Auto Scaling User Guide*.

.. _`Monitoring Your Auto Scaling Groups and Instances Using Amazon CloudWatch`: https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-instance-monitoring.html
