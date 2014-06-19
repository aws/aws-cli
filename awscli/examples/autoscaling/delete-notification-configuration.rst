**To delete an Auto Scaling notification**

The following ``delete-notification-configuration`` command deletes a notification from an Auto Scaling group::

	aws autoscaling delete-notification-configuration --auto-scaling-group-name basic-auto-scaling-group --topic-arn arn:aws:sns:us-west-2:896650972448:second-test-topic

For more information, see the `Delete Notification Configuration`_ section in the Getting Notifications When Your Auto Scaling Group Changes topic, in the *Auto Scaling Developer Guide*.

.. _`Delete Notification Configuration`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/ASGettingNotifications.html#delete-settingupnotifications

