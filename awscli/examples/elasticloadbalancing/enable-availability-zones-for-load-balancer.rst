**To enable availability zone for your load balancer**

This example adds specified availability zone to your load balancer.

Command::

    aws elb enable-availability-zones-for-load-balancer --load-balancer-name MyLoadBalancer  --availability-zones us-east-1a

Output::

    {
      "AvailabilityZones": [
        "us-east-1a",
        "us-east-1b"
      ]
    }

