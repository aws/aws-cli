**To detach load balancers from subnets**

The following ``detach-load-balancer-from-subnets`` example detaches the specified load balancer from the specified subnet. ::

    aws elb detach-load-balancer-from-subnets \
        --load-balancer-name my-load-balancer \
        --subnets subnet-0ecac448

Output::

    {
        "Subnets": [
            "subnet-15aaab61"
        ]
    }

For more information, see `Configure subnets for your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-manage-subnets.html>`__ in the *Classic Load Balancers User Guide*.
