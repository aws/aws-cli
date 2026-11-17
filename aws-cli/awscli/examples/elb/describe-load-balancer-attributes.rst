**To describe the attributes of a load balancer**

The following ``describe-load-balancer-attributes`` example describes the attributes of the specified load balancer. ::

    aws elb describe-load-balancer-attributes \
        --load-balancer-name my-load-balancer

Output::

    {
        "LoadBalancerAttributes": {
            "ConnectionDraining": {
                "Enabled": false,
                "Timeout": 300
            },
            "CrossZoneLoadBalancing": {
                "Enabled": true
            },
            "ConnectionSettings": {
                "IdleTimeout": 30
            },
            "AccessLog": {
                "Enabled": false
            }
        }
    }

For more information, see `Configure your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-configure-load-balancer.html>`__ in the *Classic Load Balancers User Guide*.
