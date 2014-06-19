**To replace the current policies associated with a specified port on your back-end instance**

This example replaces the existing policies associated with a port on your back-end instance.

Command::

  aws elb set-load-balancer-policies-for-backend-server --load-balancer-name MyLoadBalancer --instance-port 80 --policy-names EnableProxyProtocol

Output::

  {}

**To remove all policies associated with a specified port on your back-end instance**

This example removes all policies associated with a specified port on your back-end instance.

Command::

  aws elb set-load-balancer-policies-for-backend-server --load-balancer-name MyLoadBalancer --instance-port 80 --policy-names []


To confirm that all the policies associated with a specified port on your back-end instance are removed, use the
''describe-load-balancer-policies'' command and specify the name of your load balancer.

