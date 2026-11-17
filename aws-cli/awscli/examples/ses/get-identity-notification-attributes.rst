**To get the Amazon SES notification attributes for a list of identities**

The following ``get-identity-notification-attributes`` example retrieves the Amazon SES notification attributes for a list of identities. ::

    aws ses get-identity-notification-attributes \
        --identities "user1@example.com" "user2@example.com"

Output::

    {
        "NotificationAttributes": {
            "user1@example.com": {
                "ForwardingEnabled": false,
                "ComplaintTopic": "arn:aws:sns:us-west-2:EXAMPLE65304:MyTopic",
                "BounceTopic": "arn:aws:sns:us-west-2:EXAMPLE65304:MyTopic",
                "DeliveryTopic": "arn:aws:sns:us-west-2:EXAMPLE65304:MyTopic"
            },
            "user2@example.com": {
                "ForwardingEnabled": true
            }
        }
    }

This command returns the status of email feedback forwarding and, if applicable, the Amazon Resource Names (ARNs) of the Amazon SNS topics that bounce, complaint, and delivery notifications are sent to.

If you call this command with an identity that you have never submitted for verification, that identity won't appear in the output.

For more information, see `Setting up event notifications for Amazon SES <https://docs.aws.amazon.com/ses/latest/dg/monitor-sending-activity-using-notifications.html>`__ in the *Amazon Simple Email Service Developer Guide*.
