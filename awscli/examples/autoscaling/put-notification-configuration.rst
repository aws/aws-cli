**To add an Auto Scaling notification**

This example adds the specified notification to the specified Auto Scaling group::

    aws autoscaling put-notification-configuration --auto-scaling-group-name my-auto-scaling-group --topic-arn arn:aws:sns:us-west-2:123456789012:my-sns-topic --notification-type autoscaling:TEST_NOTIFICATION

For more information, see `Getting Amazon SNS Notifications When Your Auto Scaling Group Scales`_ in the *Amazon EC2 Auto Scaling User Guide*.

.. _`Getting Amazon SNS Notifications When Your Auto Scaling Group Scales`: https://docs.aws.amazon.com/autoscaling/ec2/userguide/ASGettingNotifications.html#as-configure-asg-for-sns
