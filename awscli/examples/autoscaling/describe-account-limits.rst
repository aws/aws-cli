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

For more information, see `Auto Scaling Limits`_ in the *Auto Scaling Developer Guide*.

.. _`Auto Scaling Limits`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-account-limits.html
