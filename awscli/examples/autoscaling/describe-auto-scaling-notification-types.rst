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

For more information, see `Getting Amazon SNS Notifications When Your Auto Scaling Group Scales`_ in the *Amazon EC2 Auto Scaling User Guide*.

.. _`Getting Amazon SNS Notifications When Your Auto Scaling Group Scales`: https://docs.aws.amazon.com/autoscaling/ec2/userguide/ASGettingNotifications.html
