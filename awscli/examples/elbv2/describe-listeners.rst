**Example 1: To describe a listener**

The following ``describe-listeners`` example describes the specified listener. ::

    aws elbv2 describe-listeners \
        --listener-arns arn:aws:elasticloadbalancing:us-west-2:123456789012:listener/app/my-load-balancer/50dc6c495c0c9188/f2f7dc8efc522ab2

Output::

    {
        "Listeners": [
            {
                "Port": 80,
                "Protocol": "HTTP",
                "DefaultActions": [
                    {
                        "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067",
                        "Type": "forward"
                    }
                ],
                "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188",
                "ListenerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:listener/app/my-load-balancer/50dc6c495c0c9188/f2f7dc8efc522ab2"
            }
        ]
    }

**Example 2: To describe the listeners for a load balancer**

The following ``describe-listeners`` example describes the listeners for the specified load balancer. ::

    aws elbv2 describe-listeners \
        --load-balancer-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188

Output::

    {
        "Listeners": [
            {
                "Port": 443,
                "Protocol": "HTTPS",
                "DefaultActions": [
                    {
                        "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067",
                        "Type": "forward"
                    }
                ],
                "SslPolicy": "ELBSecurityPolicy-2015-05",
                "Certificates": [
                    {
                        "CertificateArn": "arn:aws:iam::123456789012:server-certificate/my-server-cert"
                    }
                ],
                "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188",
                "ListenerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:listener/app/my-load-balancer/50dc6c495c0c9188/0467ef3c8400ae65"
            },
            {
                "Port": 80,
                "Protocol": "HTTP",
                "DefaultActions": [
                    {
                        "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067",
                        "Type": "forward"
                    }
                ],
                "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188",
                "ListenerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:listener/app/my-load-balancer/50dc6c495c0c9188/f2f7dc8efc522ab2"
            }
        ]
    }

For more information, see `Listeners for your Application Load Balancers <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-listeners.html>`__ in the *Application Load Balancers Guide*.
