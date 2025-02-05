**To disassociates a channel**

The following ``disassociate-channel`` example disassociates a Channel from a specified NotificationConfiguration. ::

    aws notifications disassociate-channel \
        --notification-configuration-arn arn:aws:notifications::123456789012:configuration/a01jjzhee9p37n8gc2ke1mr5zjx \
        --arn arn:aws:chatbot::123456789012:chat-configuration/slack-channel/Slack-CW-Events-Integration

This command produces no output.

For more information, see `Editing notification configurations in AWS User Notifications <https://docs.aws.amazon.com/notifications/latest/userguide/edit-notifications.html>`__ in the *AWS User Notifications User Guide*.