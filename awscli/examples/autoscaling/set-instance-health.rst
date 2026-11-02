**To set the health status of an instance**

The following ``set-instance-health`` example sets the health status of the specified instance to ``Unhealthy``. ::

    aws autoscaling set-instance-health \
        --instance-id i-061c63c5eb45f0416 \
        --health-status Unhealthy

This command produces no output.

For more information, see `Set up a custom health check for your Auto Scaling group <https://docs.aws.amazon.com/autoscaling/ec2/userguide/set-up-a-custom-health-check.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.
