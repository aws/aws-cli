**To enable or disable bounce and complaint email feedback forwarding for an Amazon SES verified identity**

The following ``set-identity-feedback-forwarding-enabled`` example enables a verified email address to receive bounce and complaint notifications by email. ::

    aws ses set-identity-feedback-forwarding-enabled \
        --identity user@example.com \
        --forwarding-enabled

This command produces no output.

You are required to receive bounce and complaint notifications via either Amazon SNS or email feedback forwarding, so you can only disable email feedback forwarding if you select an Amazon SNS topic for both bounce and complaint notifications.

For more information, see `Receiving Amazon SES notifications through email <https://docs.aws.amazon.com/ses/latest/dg/monitor-sending-activity-using-notifications-email.html>`__ in the *Amazon Simple Email Service Developer Guide*.
