**To get a list of suggested domain names**

The following ``get-domain-suggestions`` command returns a list of 10 suggested domain names based on the domain name ``example.com``. The response includes only domain names that are available::

  aws route53domains get-domain-suggestions --region us-east-1 --domain-name example.com --suggestion-count 10 --only-available

The following ``get-domain-suggestions`` command returns a list of 50 suggested domain names (the maximum) based on the domain name ``example.com``. The response includes both domain names that are available and domain names that aren't available::

  aws route53domains get-domain-suggestions --region us-east-1 --domain-name example.com --suggestion-count 50 --no-only-available
  
If the default region is us-east-1, you can omit the ``region`` parameter.