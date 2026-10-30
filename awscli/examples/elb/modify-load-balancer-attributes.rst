**To modify the attributes of a load balancer**

The following ``modify-load-balancer-attributes`` example modifies the ``CrossZoneLoadBalancing`` attribute of the specified load balancer. ::

    aws elb modify-load-balancer-attributes --load-balancer-name my-load-balancer --load-balancer-attributes "{\"CrossZoneLoadBalancing\":{\"Enabled\":true}}"

Output::

    {
        "LoadBalancerAttributes": {
            "CrossZoneLoadBalancing": {
                "Enabled": true
            }
        },
        "LoadBalancerName": "my-load-balancer"
    }

The following ``modify-load-balancer-attributes`` example modifies the ``ConnectionDraining`` attribute of the specified load balancer. ::

    aws elb modify-load-balancer-attributes --load-balancer-name my-load-balancer --load-balancer-attributes "{\"ConnectionDraining\":{\"Enabled\":true,\"Timeout\":300}}"

Output::

    {
        "LoadBalancerAttributes": {
            "ConnectionDraining": {
                "Enabled": true,
                "Timeout": 300
            }
        },
        "LoadBalancerName": "my-load-balancer"
    }
