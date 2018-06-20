**To disable the transfer lock on a domain**

The following ``disable-domain-transfer-lock`` command  removes the transfer lock on the domain ``example.com`` (specifically the clientTransferProhibited status) to allow the domain to be transferred to another domain registrar::

  aws route53domains disable-domain-transfer-lock --region us-east-1 --domain-name example.com
  
If the default region is us-east-1, you can omit the ``region`` parameter.

For more information, see `Transferring a Domain from Amazon Route 53 to Another Registrar`_ in the *Amazon Route 53 Developer Guide*.

.. _`Transferring a Domain from Amazon Route 53 to Another Registrar`: http://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-transfer-from-route-53.html
