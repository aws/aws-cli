**To describe the Auto Scaling notification types**

This example describes the available notification types::

    aws autoscaling describe-auto-scaling-notification-types

The following is example output::

    {
        "AutoScalingNotificationTypes": [
            "autoscaling:EC2_INSTANCE_LAUNCH",
            "autoscaling:EC2_INSTANCE_LAUNCH_ERROR",
            "autoscaling:EC2_INSTANCE_TERMINATE",
            "autoscaling:EC2_INSTANCE_TERMINATE_ERROR",
            "autoscaling:TEST_NOTIFICATION"
        ]
    }

For more information, see `Configure Your Auto Scaling Group to Send Notifications`_ in the *Auto Scaling Developer Guide*.

.. _`Configure Your Auto Scaling Group to Send Notifications`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/ASGettingNotifications.html#as-configure-asg-for-sns
