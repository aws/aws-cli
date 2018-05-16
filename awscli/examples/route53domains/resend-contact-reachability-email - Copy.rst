**To resend the confirmation email to the current email address for the registrant contact**

The following ``resend-contact-reachability-email`` command resends the confirmation email to the current email address for the registrant contact for the example.com domain::

  aws route53 resend-contact-reachability-email --region us-east-1 --domain-name example.com

If the default region is us-east-1, you can omit the ``region`` parameter.

For more information, see `Resending Authorization and Confirmation Emails`_ in the *Amazon Route 53 Developer Guide*.

.. _`Resending Authorization and Confirmation Emails`: http://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-click-email-link.html

