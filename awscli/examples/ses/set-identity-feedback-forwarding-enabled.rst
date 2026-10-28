**To enable or disable bounce and complaint email feedback forwarding for an Amazon SES verified identity**

The following ``set-identity-feedback-forwarding-enabled`` example enables a verified email address to receive bounce and complaint notifications by email. This command produces no output. ::

    aws ses set-identity-feedback-forwarding-enabled \
        --identity user@example.com \
        --forwarding-enabled

You are required to receive bounce and complaint notifications via either Amazon SNS or email feedback forwarding, so you can only disable email feedback forwarding if you select an Amazon SNS topic for both bounce and complaint notifications.

For more information about notifications, see `Using Notifications With Amazon SES`_ in the *Amazon Simple Email Service Developer Guide*.

.. _`Using Notifications With Amazon SES`: http://docs.aws.amazon.com/ses/latest/DeveloperGuide/notifications.html

