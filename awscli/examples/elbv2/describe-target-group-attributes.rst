**To describe target group attributes**

The following ``describe-target-group-attributes`` example displays the attributes of the specified target group. ::

    aws elbv2 describe-target-group-attributes \
        --target-group-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067

The output includes the attributes if the protocol is HTTP or HTTPS and the target type is ``instance`` or ``ip``.

Output::

    {
        "Attributes": [
            {
                "Value": "false",
                "Key": "stickiness.enabled"
            },
            {
                "Value": "300",
                "Key": "deregistration_delay.timeout_seconds"
            },
            {
                "Value": "lb_cookie",
                "Key": "stickiness.type"
            },
            {
                "Value": "86400",
                "Key": "stickiness.lb_cookie.duration_seconds"
            },
            {
                "Value": "0",
                "Key": "slow_start.duration_seconds"
            }
        ]
    }

The following output includes the attributes if the protocol is HTTP or HTTPS and the target type is ``lambda``.

Output::

    {
        "Attributes": [
            {
                "Value": "false",
                "Key": "lambda.multi_value_headers.enabled"
            }
        ]
    }

The following output includes the attributes if the protocol is TCP, TLS, UDP, or TCP_UDP.

Output::

    {
        "Attributes": [
            {
                "Value": "false",
                "Key": "proxy_protocol_v2.enabled"
            },
            {
                "Value": "300",
                "Key": "deregistration_delay.timeout_seconds"
            }
        ]
    }

For more information, see `Edit target group attributes for your Application Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-target-group-attributes.html>`__ in the *Application Load Balancers Guide*.
