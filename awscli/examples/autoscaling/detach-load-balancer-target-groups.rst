**To detach a target group from an Auto Scaling group**

This example detaches the specified target group from the specified Auto Scaling group::

    aws autoscaling detach-load-balancer-target-groups --auto-scaling-group-name my-auto-scaling-group --target-group-arns arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067
