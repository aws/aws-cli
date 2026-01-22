**To create an eventrule**

The following ``create-event-rule`` example creates an event rule associated with a specified NotificationConfiguration. ::

    aws notifications create-event-rule \
        --notification-configuration-arn arn:aws:notifications::123456789012:configuration/a01jjzj251d2wxsss2wvtvxethb \
        --source aws.health \
        --event-type "AWS Health Event" \
        --regions us-east-1

Output::

    {
        "arn": "arn:aws:notifications::123456789012:configuration/a01jjzj251d2wxsss2wvtvxethb/rule/a01jjzkdcbfq2chvmramvnv28nm",
        "notificationConfigurationArn": "arn:aws:notifications::123456789012:configuration/a01jjzj251d2wxsss2wvtvxethb",
        "statusSummaryByRegion": {
            "us-east-1": {
                "status": "CREATING",
                "reason": ""
            }
        }
    }

For more information, see `Creating your first notification configuration in AWS User Notifications <https://docs.aws.amazon.com/notifications/latest/userguide/getting-started.html>`__ in the *AWS User Notifications User Guide*.