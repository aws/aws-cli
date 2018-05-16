**To list all the traffic policy instances that you created in a specified hosted zone**

The following ``list-traffic-policy-instances-by-hosted-zone`` command lists summary information for all the traffic policy instances that you created in a specified hosted zone::

  aws route53 list-traffic-policy-instances-by-hosted-zone --hosted-zone-id Z1D6337EXAMPLE

If you have more than 100 traffic policy instances in a hosted zone, or if you want to list instances in groups smaller than 100, include the ``maxitems`` parameter. For example, to list traffic policy instances one at a time, use the following command::

  aws route53 list-traffic-policy-instances-by-hosted-zone --hosted-zone-id Z1D6337EXAMPLE --max-items 1

To view information about the next traffic policy instance, include the following values in the request: 

* Get the value of ``TrafficPolicyInstanceNameMarker`` from the response to the previous command, and include it in the ``traffic-policy-instance-name-marker`` parameter.
* Get the value of ``TrafficPolicyInstanceTypeMarker`` from the response to the previous command, and include it in the ``traffic-policy-instance-type-marker`` parameter.

For example::

  aws route53 list-traffic-policy-instances-by-hosted-zone --hosted-zone-id Z1D6337EXAMPLE --max-items 1 --traffic-policy-instance-name-marker apex.example.com --traffic-policy-instance-type-marker AAAA