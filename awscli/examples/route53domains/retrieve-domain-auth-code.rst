**To get the authorization code for a domain so you can transfer the domain to another registrar**

The following ``retrieve-domain-auth-code`` command gets the current authorization code for the example.com domain. You give this value to another domain registrar when you want to transfer the domain to that registrar::

  aws route53 retrieve-domain-auth-code --region us-east-1 --domain-name example.com

If the default region is us-east-1, you can omit the ``region`` parameter.

For more information, see `Transferring a Domain from Amazon Route 53 to Another Registrar`_ in the *Amazon Route 53 Developer Guide*.

.. _`Transferring a Domain from Amazon Route 53 to Another Registrar`: http://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-transfer-from-route-53.html

