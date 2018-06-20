**To determine whether the registrant contact has responded to a confirmation email**

The following ``get-contact-reachability-status`` command returns information about whether the registrant contact for ``example.com`` has responded to a confirmation email::

  aws route53domains get-contact-reachability-status --region us-east-1 --domain-name example.com
  
If the default region is us-east-1, you can omit the ``region`` parameter.

For more information, see `Resending Authorization and Confirmation Emails`_ in the *Amazon Route 53 Developer Guide*.

.. _`Resending Authorization and Confirmation Emails`: https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-click-email-link.html
