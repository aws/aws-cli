**To update an existing eventrule**

The following ``update-event-rule`` example updates an existing event rule that is associated with a specified NotificationConfiguration. ::

    aws notifications update-event-rule \
        --arn "arn:aws:notifications::123456789012:configuration/a01jjzj251d2wxsss2wvtvxethb/rule/a01jjzkdcbfq2chvmramvnv28nm" \
        --event-pattern "{\"source\":[\"aws.ec2\"],\"detail-type\":[\"EC2 Instance State-change Notification\"]}"

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

For more information, see `Editing notification configurations in AWS User Notifications <https://docs.aws.amazon.com/notifications/latest/userguide/edit-notifications.html>`__ in the *AWS User Notifications User Guide*.