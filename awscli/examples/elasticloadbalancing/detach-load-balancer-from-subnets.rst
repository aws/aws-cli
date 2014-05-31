**To detach load balancer from subnets**

This example detaches your load balancer from the specified subnets in your Amazon VPC.

Command::

     aws elb detach-load-balancer-from-subnets --load-balancer-name MyVPCLoadBalancer --subnets subnet-0ecac448


Output::

   {
      "Subnets": [
        "subnet-15aaab61"
      ]
   }

