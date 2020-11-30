**To enable metrics collection for an Auto Scaling group**

This example enables data collection for the specified Auto Scaling group. ::

    aws autoscaling enable-metrics-collection --auto-scaling-group-name my-asg --granularity "1Minute"

To collect data for a specific metric, use the ``--metrics`` option. ::

    aws autoscaling enable-metrics-collection --auto-scaling-group-name my-asg --metrics GroupDesiredCapacity --granularity "1Minute"

This command returns to the prompt if successful.

For more information, see `Monitoring CloudWatch metrics for your Auto Scaling groups and instances`_ in the *Amazon EC2 Auto Scaling User Guide*.

.. _`Monitoring CloudWatch metrics for your Auto Scaling groups and instances`: https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-instance-monitoring.html
