**To delete an eventrule**

The following ``delete-event-rule`` example deletes an EventRule associated to a specific NotificationConfiguration. ::

    aws notifications delete-event-rule \
        --arn arn:aws:notifications::123456789012:configuration/a01jjzj251d2wxsss2wvtvxethb/rule/a01jjzkdcbfq2chvmramvnv28nm

This command produces no output.

For more information, see `Deleting notification configurations in AWS User Notifications <https://docs.aws.amazon.com/notifications/latest/userguide/delete-notifications.html>`__ in the *AWS User Notifications User Guide*.