**To create listeners for a load balancer**

This example creates a listener for your load balancer at port 80 using the HTTP protocol.

Command::

     aws elb create-load-balancer-listeners --load-balancer-name my-load-balancer --listeners "Protocol=HTTP,LoadBalancerPort=80,InstanceProtocol=HTTP,InstancePort=80"

