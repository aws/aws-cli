**To list all the traffic policy instances that you created using a specified traffic policy version**

The following ``list-traffic-policy-instances-by-policy`` command lists summary information for all the traffic policy instances that you created using a specified traffic policy version::

  aws route53 list-traffic-policy-instances-by-policy --traffic-policy-id 2d826c42-c6c8-4679-893f-28351EXAMPLE --traffic-policy-version 3

If you created more than 100 traffic policy instances using the same policy, or if you want to list instances in groups smaller than 100, include the ``maxitems`` parameter. For example, to list traffic policy instances one at a time, use the following command::

  aws route53 list-traffic-policy-instances-by-policy --traffic-policy-id 2d826c42-c6c8-4679-893f-28351EXAMPLE --traffic-policy-version 3 --max-items 1

To view information about the next traffic policy instance, include the following values in the request: 

* Get the value of ``HostedZoneIdMarker`` from the response to the previous command, and include it in the ``hosted-zone-id-marker`` parameter.
* Get the value of ``TrafficPolicyInstanceNameMarker`` from the response to the previous command, and include it in the ``traffic-policy-instance-name-marker`` parameter.
* Get the value of ``TrafficPolicyInstanceTypeMarker`` from the response to the previous command, and include it in the ``traffic-policy-instance-type-marker`` parameter.

For example::

  aws route53 list-traffic-policy-instances-by-policy --traffic-policy-id 2d826c42-c6c8-4679-893f-28351EXAMPLE --traffic-policy-version 3 --max-items 1 --hosted-zone-id-marker Z1D6337EXAMPLE --traffic-policy-instance-name-marker apex.example.com --traffic-policy-instance-type-marker AAAA