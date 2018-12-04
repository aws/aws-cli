**To describe the load balancers for an Auto Scaling group**

This example describes the load balancers for the specified Auto Scaling group::

    aws autoscaling describe-load-balancers --auto-scaling-group-name my-auto-scaling-group

The following is example output::

    {
        "LoadBalancers": [
            {
                "State": "Added",
                "LoadBalancerName": "my-load-balancer"
            }
        ]
    }
