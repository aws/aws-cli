**To list the domains that are registered with the current AWS account**

The following ``list-domains`` command lists summary information about the first 100 domains that are registered with the current AWS account::

  aws route53domains list-domains --region us-east-1

If you have more than 100 domains, or if you want to list domains in groups smaller than 100, include the ``--maxitems`` parameter. For example, to list domains one at a time, use the following command::

  aws route53domains list-domains --region us-east-1 --max-items 1

To view information about the next domain, take the value of ``NextPageMarker`` from the response to the previous command, and include it in the ``--starting-token`` parameter, for example::

  aws route53domains list-domains --region us-east-1 --max-items 1 --starting-token eyJNYXJrZXIiOiBudWxsLCAiYm90b190cnVuY2F0ZV9hbW91bnQEXAMPLE==
  
If the default region is us-east-1, you can omit the ``region`` parameter.