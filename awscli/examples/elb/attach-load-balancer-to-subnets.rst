**To attach subnets to a load balancer**

This example adds a subnet to the configured subnets in the Amazon VPC for the load balancer.


Command::

  aws elb attach-load-balancer-to-subnets --load-balancer MyVPCLoadBalancer --subnets subnet-0ecac448

Output::

   {
      "Subnets": [
        "subnet-15aaab61",
        "subnet-0ecac448"
      ]
   }

