**To modify the attributes of a load balancer**

The following ``modify-load-balancer-attributes`` example modifies the ``CrossZoneLoadBalancing`` attribute of the specified load balancer. ::

    aws elb modify-load-balancer-attributes \
        --load-balancer-name my-load-balancer \
        --load-balancer-attributes "{\"CrossZoneLoadBalancing\":{\"Enabled\":true}}"

Output::

    {
        "LoadBalancerAttributes": {
            "CrossZoneLoadBalancing": {
                "Enabled": true
            }
        },
        "LoadBalancerName": "my-load-balancer"
    }

For more information, see `Configure cross-zone load balancing for your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/enable-disable-crosszone-lb.html>`__ in the *Classic Load Balancers Guide*.

The following ``modify-load-balancer-attributes`` example modifies the ``ConnectionDraining`` attribute of the specified load balancer. ::

    aws elb modify-load-balancer-attributes \
        --load-balancer-name my-load-balancer \
        --load-balancer-attributes "{\"ConnectionDraining\":{\"Enabled\":true,\"Timeout\":300}}"

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

For more information, see `Configure connection draining for your Classic Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/config-conn-drain.html>`__ in the *Classic Load Balancers Guide*.
