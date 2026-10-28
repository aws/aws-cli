**To describe the Classic Load Balancers for an Auto Scaling group**

The following ``describe-load-balancers`` example describes the Classic Load Balancers for the specified Auto Scaling group. ::

    aws autoscaling describe-load-balancers \
        --auto-scaling-group-name my-asg

Output::

    {
        "LoadBalancers": [
            {
                "State": "Added",
                "LoadBalancerName": "my-load-balancer"
            }
        ]
    }
