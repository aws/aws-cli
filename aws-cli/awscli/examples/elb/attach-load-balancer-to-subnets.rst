**To attach subnets to a load balancer**

The following ``attach-load-balancer-to-subnets`` example adds the specified subnet to the set of configured subnets for the specified load balancer. ::

    aws elb attach-load-balancer-to-subnets \
        --load-balancer-name my-load-balancer \
        --subnets subnet-0ecac448

Output::

    {
        "Subnets": [
            "subnet-15aaab61",
            "subnet-0ecac448"
        ]
    }

For more information, see `Configure subnets for your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-manage-subnets.html>`__ in the *Classic Load Balancers User Guide*.
