**To retrieve a list of notification rules**

The following ``list-notification-rules`` example retrieves a list of all notification rules in the current AWS Region. ::

    aws codestar-notifications list-notification-rules

Output::

    {
        "NotificationRules": [
            {
                "Id": "dc82df7a-EXAMPLE",
                "Arn": "arn:aws:codestar-notifications:us-west-2:123456789012:notificationrule/dc82df7a-EXAMPLE"
            },
            {
                "Id": "8d1f0983-EXAMPLE",
                "Arn": "arn:aws:codestar-notifications:us-west-2:123456789012:notificationrule/8d1f0983-EXAMPLE"
            }
        ]
    }

For more information, see `View Notification Rules <https://docs.aws.amazon.com/codestar-notifications/latest/userguide/notification-rule-view.html>`__ in the *AWS Developer Tools Console User Guide*.
