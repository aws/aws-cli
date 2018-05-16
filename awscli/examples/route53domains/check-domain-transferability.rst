**To determine whether a domain can be transferred to Route 53**

The following ``check-domain-transferability`` command returns information about whether you can transfer the domain name ``example.com`` to Route 53::

  aws route53domains check-domain-transferability --region us-east-1 --domain-name example.com

If the default region is us-east-1, you can omit the ``region`` parameter.