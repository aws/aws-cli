**To disable metrics collection for an Auto Scaling group**

The following ``disable-metrics-collection`` example disables collection of the ``GroupDesiredCapacity`` metric for the specified Auto Scaling group. ::

    aws autoscaling disable-metrics-collection \
        --auto-scaling-group-name my-asg \
        --metrics GroupDesiredCapacity

This command produces no output.

For more information, see `Monitor CloudWatch metrics for your Auto Scaling groups and instances <https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-cloudwatch-monitoring.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.
