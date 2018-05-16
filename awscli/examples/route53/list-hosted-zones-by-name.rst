**To list hosted zones by name that are associated with the current AWS account**

The following ``list-hosted-zones-by-name`` command lists summary information about the first 100 hosted zones that are associated with the current AWS account.::

  aws route53 list-hosted-zones-by-name

If you have more than 100 hosted zones, or if you want to list them in groups smaller than 100, include the ``--maxitems`` parameter. For example, to list hosted zones one at a time, use the following command::

  aws route53 list-hosted-zones-by-name --max-items 1

If the value of ``IsTruncated`` is ``true``, then there are more hosted zones to list. To list information about the next ``max-items`` hosted zones, get the values of ``NextHostedZoneId`` and ``NextDNSName`` from the response to the previous request. Then include the values in the ``hosted-zone-id`` and ``dns-name`` parameters in the next request. For example, if the previous response had values of ``Z20PDX1EXAMPLE`` for ``NextHostedZoneId`` and ``example.com`` for ``NextDNSName``, then you'd submit the following request to get the next ``max-items`` hosted zones::

  aws route53 list-hosted-zones-by-name --max-items 1 --hosted-zone-id Z20PDX1EXAMPLE --dns-name example.com