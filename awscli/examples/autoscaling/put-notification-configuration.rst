**To add an Auto Scaling notification**

This example adds the specified notification to the specified Auto Scaling group::

    aws autoscaling put-notification-configuration --auto-scaling-group-name my-auto-scaling-group --topic-arn arn:aws:sns:us-west-2:123456789012:my-sns-topic --notification-type autoscaling:TEST_NOTIFICATION

For more information, see `Configure Your Auto Scaling Group to Send Notifications`_ in the *Auto Scaling Developer Guide*.

.. _`Configure Your Auto Scaling Group to Send Notifications`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/ASGettingNotifications.html#as-configure-asg-for-sns
