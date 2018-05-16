**To get the limit on the number of hosted zones that you can associate with a specified reusable delegation set**

The following ``get-reusable-delegation-set-limit`` command gets the current limit on the number of hosted zones that you can associate with a reusable delegation set with a ``delegation-set-id`` of ``/delegationset/N1OK2RWEXAMPLE``::

  aws route53 get-reusable-delegation-set-limit --type MAX_ZONES_BY_REUSABLE_DELEGATION_SET --delegation-set-id /delegationset/N1OK2RWEXAMPLE