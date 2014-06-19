**To disable availability zone from a load balancer**

This example removes specified availability zone from your load balancer. You must have at least one availability zone
enabled for your load balancer at all times.

Command::

    aws elb disable-availability-zones-for-load-balancer --load-balancer-name MyLoadBalancer  --availability-zones us-east-1a

Output::

    {
      "AvailabilityZones": [
        "us-east-1b"
      ]
    }

