**To enable Availability Zones for a load balancer**

The following ``enable-availability-zones-for-load-balancer`` example adds the specified Availability Zone to the specified load balancer. ::

    aws elb enable-availability-zones-for-load-balancer \
        --load-balancer-name my-load-balancer \
        --availability-zones us-west-2b

Output::

    {
        "AvailabilityZones": [
            "us-west-2a",
            "us-west-2b"
        ]
    }

For more information, see `Configure subnets for your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-manage-subnets.html>`__ in the *Classic Load Balancers Guide*.
