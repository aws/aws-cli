**To enable the transfer lock on a domain**

The following ``enable-domain-transfer-lock`` command enables the transfer lock on the domain ``example.com`` (specifically the clientTransferProhibited status) to prevent the domain from being transferred to another domain registrar::

  aws route53domains enable-domain-transfer-lock --region us-east-1 --domain-name example.com
  
If the default region is us-east-1, you can omit the ``region`` parameter.

For more information, see `Transferring a Domain from Amazon Route 53 to Another Registrar`_ in the *Amazon Route 53 Developer Guide*.

.. _`Transferring a Domain from Amazon Route 53 to Another Registrar`: http://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-transfer-from-route-53.html
