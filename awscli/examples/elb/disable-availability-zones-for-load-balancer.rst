**To disable Availability Zones for a load balancer**

The following ``disable-availability-zones-for-load-balancer`` example removes the specified Availability Zone from the set of Availability Zones for the specified load balancer. ::

    aws elb disable-availability-zones-for-load-balancer --load-balancer-name my-load-balancer --availability-zones us-west-2a

Output::

    {
        "AvailabilityZones": [
            "us-west-2b"
        ]
    }
