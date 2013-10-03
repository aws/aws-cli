**To get the Amazon SES notification attributes for a list of identities**

The following example uses the ``get-identity-notification-attributes`` command to retrieve the Amazon SES notification attributes for a list of identities::

    aws ses get-identity-notification-attributes --identities "user1@example.com" "user2@example.com"

Output::

 {
    "NotificationAttributes": {
        "user1@example.com": {
            "ForwardingEnabled": false,
            "ComplaintTopic": "arn:aws:sns:us-east-1:EXAMPLE65304:MyTopic",
            "BounceTopic": "arn:aws:sns:us-east-1:EXAMPLE65304:MyTopic"
        },
        "user2@example.com": {
            "ForwardingEnabled": true
        }
    }
 }

If email feedback forwarding is disabled, then this command returns the Amazon Resource Names (ARNs) of the SNS topics that bounce and complaint notifications are sent to.

If you call this command with an identity that you have never submitted for verification, that identity won't appear in the output.

For more information about bounce and complaint notifications, see `Bounce and Complaint Notifications in Amazon SES`_ in the *Amazon Simple Email Service Developer Guide*.

.. _`Bounce and Complaint Notifications in Amazon SES`: http://docs.aws.amazon.com/ses/latest/DeveloperGuide/bounce-complaint-notifications.html
