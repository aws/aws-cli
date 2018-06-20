**To list the tags for a specified health check or hosted zone**

The following ``list-tags-for-resource`` command lists tags for the health check with an ID of ``905a32be-b014-4c35-9b22-07173EXAMPLE``::

  aws route53 list-tags-for-resource --resource-type healthcheck --resource-id 905a32be-b014-4c35-9b22-07173EXAMPLE

The following ``list-tags-for-resource`` command lists tags for the hosted zone with an ID of ``Z1D6337EXAMPLE``::

  aws route53 list-tags-for-resource --resource-type hostedzone --resource-id Z1D6337EXAMPLE