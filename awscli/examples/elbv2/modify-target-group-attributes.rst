**To modify the deregistration delay timeout**

The following ``modify-target-group-attributes`` example sets the deregistration delay timeout to the specified value for the specified target group. ::

    aws elbv2 modify-target-group-attributes \
        --target-group-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067 \
        --attributes Key=deregistration_delay.timeout_seconds,Value=600

Output::

    {
        "Attributes": [
            {
                "Value": "false",
                "Key": "stickiness.enabled"
            },
            {
                "Value": "600",
                "Key": "deregistration_delay.timeout_seconds"
            },
            {
                "Value": "lb_cookie",
                "Key": "stickiness.type"
            },
            {
                "Value": "86400",
                "Key": "stickiness.lb_cookie.duration_seconds"
            }
        ]
    }

For more information, see `Edit target group attributes for your Application Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-target-group-attributes.html#deregistration-delay>`__ in the *Application Load Balancers Guide*.
