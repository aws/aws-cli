**To enable or disable email feedback forwarding for an Amazon SES verified identity**

The following example uses the ``set-identity-feedback-forwarding-enabled`` command to enable a verified email address to receive feedback notifications by email::

    aws ses set-identity-feedback-forwarding-enabled --identity user@example.com --forwarding-enabled

For more information about feedback notifications, see `Bounce and Complaint Notifications in Amazon SES`_ in the *Amazon Simple Email Service Developer Guide*.

.. _`Bounce and Complaint Notifications in Amazon SES`: http://docs.aws.amazon.com/ses/latest/DeveloperGuide/bounce-complaint-notifications.html

