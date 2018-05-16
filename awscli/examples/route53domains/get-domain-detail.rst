**To get detailed information about a specified domain**

The following ``get-domain-detail`` command returns detailed information including contact information for ``example.com``::

  aws route53domains get-domain-detail --region us-east-1 --domain-name example.com
  
If the default region is us-east-1, you can omit the ``region`` parameter.