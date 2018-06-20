**To update one or more settings for a specified version of a traffic policy instance**

The following ``update-traffic-policy-instance`` command updates the settings for a traffic policy instance with an ``id`` of ``818d7990-051f-4be1-ab93-6e031EXAMPLE``, a ``ttl`` of ``300``, a ``traffic-policy-id`` of ``2d826c42-c6c8-4679-893f-28351EXAMPLE``, and a ``traffic-policy-version`` of ``3``::

  aws route53 update-traffic-policy-instance --id 818d7990-051f-4be1-ab93-6e031EXAMPLE --ttl 300 --traffic-policy-id 2d826c42-c6c8-4679-893f-28351EXAMPLE --traffic-policy-version 3
