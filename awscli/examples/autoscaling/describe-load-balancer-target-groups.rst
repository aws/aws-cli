**To describe the load balancer target groups for an Auto Scaling group**

The following ``describe-load-balancer-target-groups`` example describes the load balancer target groups attached to the specified Auto Scaling group. ::

    aws autoscaling describe-load-balancer-target-groups \
        --auto-scaling-group-name my-asg

Output::

    {
        "LoadBalancerTargetGroups": [
            {
                "LoadBalancerTargetGroupARN": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067",
                "State": "Added"
            }
        ]
    }

For more information, see `Use Elastic Load Balancing to distribute incoming application traffic in your Auto Scaling group <https://docs.aws.amazon.com/autoscaling/ec2/userguide/autoscaling-load-balancer.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.
