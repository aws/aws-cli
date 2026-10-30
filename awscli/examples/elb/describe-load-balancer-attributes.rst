**To describe the attributes of a load balancer**

The following ``describe-load-balancer-attributes`` example describes the attributes of the specified load balancer. ::

    aws elb describe-load-balancer-attributes --load-balancer-name my-load-balancer

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

