**To create a reusable delegation set**

The following ``create-reusable-delegation-set`` command creates a reusable delegation set using the caller reference ``2018-06-01-18:47``::

  aws route53 create-reusable-delegation-set --caller-reference 2018-06-01-18:47 

The following ``create-reusable-delegation-set`` command converts the delegation set for the hosted zone ``Z1OX3WQEXAMPLE`` into a reusable delegation set::

  aws route53 create-reusable-delegation-set --caller-reference 2018-06-01-18:48 --hosted-zone-id Z1OX3WQEXAMPLE

For more information about how to use reusable delegation sets, see `CreateReusableDelegationSet`_ in the *Amazon Route 53 API Reference*.

.. _`CreateReusableDelegationSet`: http://docs.aws.amazon.com/Route53/latest/APIReference/API_CreateReusableDelegationSet.html