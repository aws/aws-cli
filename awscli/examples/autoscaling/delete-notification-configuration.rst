**To delete an Auto Scaling notification**

This example deletes the specified notification from the specified Auto Scaling group::

    aws autoscaling delete-notification-configuration --auto-scaling-group-name my-auto-scaling-group --topic-arn arn:aws:sns:us-west-2:123456789012:my-sns-topic

For more information, see `Delete the Notification Configuration`_ in the *Auto Scaling Developer Guide*.

.. _`Delete the Notification Configuration`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/ASGettingNotifications.html#delete-settingupnotifications
