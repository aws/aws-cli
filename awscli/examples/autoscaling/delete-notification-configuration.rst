**To delete an Auto Scaling notification**

This example deletes the specified notification from the specified Auto Scaling group. ::

    aws autoscaling delete-notification-configuration --auto-scaling-group-name my-asg --topic-arn arn:aws:sns:us-west-2:123456789012:my-sns-topic

This command returns to the prompt if successful.

For more information, see `Delete the notification configuration`_ in the *Amazon EC2 Auto Scaling User Guide*.

.. _`Delete the notification configuration`: https://docs.aws.amazon.com/autoscaling/ec2/userguide/ASGettingNotifications.html#delete-settingupnotifications