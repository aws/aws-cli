**To enable automatic renewal of a domain**

The following ``enable-domain-auto-renew`` command configures Route 53 to automatically renew the domain ``example.com`` before registration for the domain expires::

  aws route53domains enable-domain-auto-renew --region us-east-1 --domain-name example.com
  
If the default region is us-east-1, you can omit the ``region`` parameter.

For more information, see `Renewing Registration for a Domain`_ in the *Amazon Route 53 Developer Guide*.

.. _`Renewing Registration for a Domain`: http://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-renew.html
