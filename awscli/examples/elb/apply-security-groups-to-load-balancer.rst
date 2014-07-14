**To associate a  security group with a load balancer in Amazon VPC**

This example associates a security group with a load balancer in Amazon VPC.


Command::

   aws elb apply-security-groups-to-load-balancer  --load-balancer-name MyVPCLoadBalancer --security-groups sg-fc448899

Output::

   {
     "SecurityGroups": [
        "sg-fc448899"
     ]
   }

