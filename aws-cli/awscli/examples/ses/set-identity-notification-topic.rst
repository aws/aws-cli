**To set the Amazon SNS topic to which Amazon SES will publish bounce, complaint, and/or delivery notifications for a verified identity**

The following ``set-identity-notification-topic`` example specifies the Amazon SNS topic to which a verified email address will receive bounce notifications. ::

    aws ses set-identity-notification-topic \
        --identity user@example.com \
        --notification-type Bounce \
        --sns-topic arn:aws:sns:us-west-2:EXAMPLE65304:MyTopic

This command produces no output.

For more information, see `Configuring Amazon SNS notifications for Amazon SES <https://docs.aws.amazon.com/ses/latest/dg/configure-sns-notifications.html>`__ in the *Amazon Simple Email Service Developer Guide*.
