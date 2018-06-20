**To list reusable delegation sets**

The following ``list-reusable-delegation-sets`` command lists information about the first 100 reusable delegation sets that are associated with the current AWS account.::

  aws route53 list-reusable-delegation-sets

If you have more than 100 reusable delegation sets, or if you want to list them in groups smaller than 100, include the ``--maxitems`` parameter. For example, to list reusable delegation sets one at a time, use the following command::

  aws route53 list-reusable-delegation-sets --max-items 1

If the value of ``IsTruncated`` is true and you want to view the next reusable delegation set, get the value of ``NextMarker`` from the response to the previous command, and include it in the ``--marker`` parameter, for example::

  aws route53 list-query-logging-configs --max-items 1 --marker NXJM1TEXAMPLE