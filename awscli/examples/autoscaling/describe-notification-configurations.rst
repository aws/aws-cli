**To describe the Auto Scaling notification configurations**

This example describes the notification configurations for the specified Auto Scaling group::

    aws autoscaling describe-notification-configurations --auto-scaling-group-name my-auto-scaling-group

The following is example output::

    {
        "NotificationConfigurations": [
            {
                "AutoScalingGroupName": "my-auto-scaling-group",
                "NotificationType": "autoscaling:TEST_NOTIFICATION",
                "TopicARN": "arn:aws:sns:us-west-2:123456789012:my-sns-topic-2"
            },
            {
                "AutoScalingGroupName": "my-auto-scaling-group",
                "NotificationType": "autoscaling:TEST_NOTIFICATION",
                "TopicARN": "arn:aws:sns:us-west-2:123456789012:my-sns-topic"
            }
        ]
    }

To return a specific number of notification configurations, use the ``max-items`` parameter::

    aws autoscaling describe-notification-configurations --auto-scaling-group-name my-auto-scaling-group --max-items 1

The following is example output::

    {
        "NextToken": "Z3M3LMPEXAMPLE",
        "NotificationConfigurations": [
            {
                "AutoScalingGroupName": "my-auto-scaling-group",
                "NotificationType": "autoscaling:TEST_NOTIFICATION",
                "TopicARN": "arn:aws:sns:us-west-2:123456789012:my-sns-topic-2"
            }
        ]
    }

Use the ``NextToken`` field with the ``starting-token`` parameter in a subsequent call to get additional notification configurations::

    aws autoscaling describe-notification-configurations --auto-scaling-group-name my-auto-scaling-group --starting-token Z3M3LMPEXAMPLE

For more information, see `Getting Notifications When Your Auto Scaling Group Changes`_ in the *Auto Scaling Developer Guide*.

.. _`Getting Notifications When Your Auto Scaling Group Changes`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/ASGettingNotifications.html
