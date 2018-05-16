**To list the tags for up to 10 health checks or hosted zones**

The following ``list-tags-for-resources`` command lists tags for two health checks::

  aws route53 list-tags-for-resources --resource-type healthcheck --resource-id 905a32be-b014-4c35-9b22-07177EXAMPLE 92195cef-3378-4412-b504-09af6EXAMPLE

The following ``list-tags-for-resources`` command lists tags for two hosted zones::

  aws route53 list-tags-for-resources --resource-type hostedzone --resource-id Z2ENFY7EXAMPLE Z1OX3W7EXAMPLE