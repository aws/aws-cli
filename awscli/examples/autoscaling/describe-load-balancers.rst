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

For more information, see `Use Elastic Load Balancing to distribute incoming application traffic in your Auto Scaling group <https://docs.aws.amazon.com/autoscaling/ec2/userguide/autoscaling-load-balancer.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.
