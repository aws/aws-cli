**To replace the current policies associated with your load balancer**

This example replaces the existing policies associated with your load balancer.

Command::

  aws elb set-load-balancer-policies-of-listener --load-balancer-name MyHTTPSLoadBalancer --load-balancer-port 443 --policy-names MySSLNegotiationPolicy


Output::

 {}

**To remove all policies associated with your load balancer**

This example removes all associated policies from the specified load balancer.

Command::

  aws elb set-load-balancer-policies-of-listener --load-balancer-name MyHTTPSLoadBalancer --load-balancer-port 443 --policy-names []

To confirm that all the associated policies are removed from the load balancer, use ''describe-load-balancer-policies''
command and specify the name of your load balancer.

