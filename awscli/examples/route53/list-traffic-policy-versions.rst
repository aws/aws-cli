**To list all the traffic policy versions for a specified traffic policy**

The following ``list-traffic-policy-versions`` command lists summary information about the first 100 traffic policy versions that are associated with a specified traffic policy::

  aws route53 list-traffic-policy-versions --id 02b7c2b4-063f-4be6-922d-62f57EXAMPLE

If the specified traffic policy has more than 100 versions, or if you want to list versions in groups smaller than 100, include the ``--maxitems`` parameter. For example, to list traffic policy versions one at a time, use the following command::

  aws route53 list-traffic-policy-versions --id 02b7c2b4-063f-4be6-922d-62f57EXAMPLE --max-items 1

To view information about the next traffic policy version, take the value of ``TrafficPolicyVersionMarker`` from the response to the previous command, and include it in the ``--traffic-policy-version-marker`` parameter, for example::

  aws route53 list-traffic-policy-versions --id 02b7c2b4-063f-4be6-922d-62f57EXAMPLE --max-items 1 --traffic-policy-version-marker 1