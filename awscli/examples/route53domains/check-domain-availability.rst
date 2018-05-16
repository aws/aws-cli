**To determine whether you can register a domain name**

The following ``check-domain-availability`` command returns information about whether you can register the domain name ``example.com``::

  aws route53domains check-domain-availability --region us-east-1 --domain-name example.com

If the default region is us-east-1, you can omit the ``region`` parameter.