**To remove tags for a load balancer**

This example removes tags for a load balancer.

Command::

  aws elb remove-tags  --load-balancer-name MyTCPLoadBalancer --tag "Key=project,Value=lima"

Output::

  {}