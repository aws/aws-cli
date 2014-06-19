**To add an Auto Scaling notification**

The following ``put-notification-configuration`` command adds a notification to an Auto Scaling group::

	--auto-scaling-group-name basic-auto-scaling-group --topic-arn arn:aws:sns:us-west-2:896650972448:test-topic --notification-type autoscaling:TEST_NOTIFICATION

For more information, see the `Configure your Auto Scaling Group to Send Notifications`_ section in the Getting Notifications When Your Auto Scaling Group Changes topic, in the *Auto Scaling Developer Guide*.

.. _`Configure your Auto Scaling Group to Send Notifications`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/ASGettingNotifications.html#as-configure-asg-for-sns

