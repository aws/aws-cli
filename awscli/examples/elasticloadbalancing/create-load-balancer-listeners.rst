**To create listeners on a load balancer**

This example creates listeners on your load balancer at the specified ports using specified protocols.


Command::

     aws elb create-load-balancer-listeners --load-balancer-name MyHTTPSLoadBalancer --listeners Protocol=HTTP,LoadBalancerPort=80,InstanceProtocol=HTTP,InstancePort=80

Output::

      {}

