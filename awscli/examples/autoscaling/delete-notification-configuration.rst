**To delete an Auto Scaling notification**

This example deletes the specified notification from the specified Auto Scaling group::

    aws autoscaling delete-notification-configuration --auto-scaling-group-name my-auto-scaling-group --topic-arn arn:aws:sns:us-west-2:123456789012:my-sns-topic

For more information, see `Delete the Notification Configuration`_ in the *Amazon EC2 Auto Scaling User Guide*.

.. _`Delete the Notification Configuration`: https://docs.aws.amazon.com/autoscaling/ec2/userguide/ASGettingNotifications.html#delete-settingupnotifications
