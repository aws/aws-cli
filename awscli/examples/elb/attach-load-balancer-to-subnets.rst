**To attach subnets to a load balancer**

The following ``attach-load-balancer-to-subnets`` example adds the specified subnet to the set of configured subnets for the specified load balancer. ::

    aws elb attach-load-balancer-to-subnets --load-balancer-name my-load-balancer --subnets subnet-0ecac448

Output::

    {
        "Subnets": [
            "subnet-15aaab61",
            "subnet-0ecac448"
        ]
    }

