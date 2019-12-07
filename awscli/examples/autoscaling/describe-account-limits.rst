**To describe your Auto Scaling account limits**

This example describes the Auto Scaling limits for your AWS account::

    aws autoscaling describe-account-limits

The following is example output::

    {
        "NumberOfLaunchConfigurations": 5,
        "MaxNumberOfLaunchConfigurations": 100,
        "NumberOfAutoScalingGroups": 3,
        "MaxNumberOfAutoScalingGroups": 20
    }

For more information, see `Amazon EC2 Auto Scaling Limits`_ in the *Amazon EC2 Auto Scaling User Guide*.

.. _`Amazon EC2 Auto Scaling Limits`: https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-account-limits.html
