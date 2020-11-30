**To describe the Classic Load Balancers for an Auto Scaling group**

This example describes the Classic Load Balancers for the specified Auto Scaling group. ::

    aws autoscaling describe-load-balancers --auto-scaling-group-name my-asg

The following is example output::

    {
        "LoadBalancers": [
            {
                "State": "Added",
                "LoadBalancerName": "my-load-balancer"
            }
        ]
    }
