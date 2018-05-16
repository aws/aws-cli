**To get the number of traffic policy instances that are associated with the current AWS account**

The following ``get-traffic-policy-instance-count`` command gets the number of traffic policy instances that are associated with the current AWS account::

  aws route53 get-traffic-policy-instance-count

The number includes all traffic policy instances, regardless of the traffic policies that the instances were created with or the hosted zones that the records appear in.