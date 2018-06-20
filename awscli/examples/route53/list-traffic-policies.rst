**To list the traffic policies that are associated with the current AWS account**

The following ``list-traffic-policies`` command lists summary information about the first 100 traffic policies that are associated with the current AWS account::

  aws route53 list-traffic-policies

If you have more than 100 traffic policies, or if you want to list them in groups smaller than 100, include the ``--maxitems`` parameter. For example, to list traffic policies one at a time, use the following command::

  aws route53 list-traffic-policies --max-items 1

To view information about the next traffic policy, take the value of ``TrafficPolicyIdMarker`` from the response to the previous command, and include it in the ``--traffic-policy-id-marker`` parameter, for example::

  aws route53 list-traffic-policies --max-items 1 --traffic-policy-id-marker 2d826c42-c6c8-4679-893f-28351EXAMPLE