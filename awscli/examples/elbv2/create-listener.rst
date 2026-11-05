**Example 1: To create an HTTP listener**

The following ``create-listener`` example creates an HTTP listener for the specified Application Load Balancer that forwards requests to the specified target group. ::

    aws elbv2 create-listener \
        --load-balancer-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188 \
        --protocol HTTP \
        --port 80 \
        --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067

Output::

    {
        "Listeners": [
            {
                "ListenerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:listener/app/my-load-balancer/50dc6c495c0c9188/f2f7dc8efc522ab2",
                "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188",
                "Port": 80,
                "Protocol": "HTTP",
                "DefaultActions": [
                    {
                        "Type": "forward",
                        "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067",
                        "ForwardConfig": {
                            "TargetGroups": [
                                {
                                    "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067",
                                    "Weight": 1
                                }
                            ],
                            "TargetGroupStickinessConfig": {
                                "Enabled": false
                            }
                        }
                    }
                ]
            }
        ]
    }

For more information, see `Create an HTTP listener for your Application Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/create-listener.html>`__ in the *Application Load Balancers Guide*.

**Example 2: To create an HTTPS listener**

The following ``create-listener`` example creates an HTTPS listener for the specified Application Load Balancer that forwards requests to the specified target group. You must specify an SSL certificate for an HTTPS listener. You can create and manage certificates using AWS Certificate Manager (ACM). Alternatively, you can create a certificate using SSL/TLS tools, get the certificate signed by a certificate authority (CA), and upload the certificate to AWS Identity and Access Management (IAM). ::

    aws elbv2 create-listener \
        --load-balancer-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188 \
        --protocol HTTPS \
        --port 443 \
        --certificates CertificateArn=arn:aws:acm:us-west-2:123456789012:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --ssl-policy ELBSecurityPolicy-2016-08 \
        --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067

Output::

    {
        "Listeners": [
            {
                "ListenerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:listener/app/my-load-balancer/50dc6c495c0c9188/0467ef3c8400ae65",
                "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188",
                "Port": 443,
                "Protocol": "HTTPS",
                "Certificates": [
                    {
                        "CertificateArn": "arn:aws:acm:us-west-2:123456789012:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
                    }
                ],
                "SslPolicy": "ELBSecurityPolicy-2016-08",
                "DefaultActions": [
                    {
                        "Type": "forward",
                        "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067",
                        "ForwardConfig": {
                            "TargetGroups": [
                                {
                                    "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067",
                                    "Weight": 1
                                }
                            ],
                            "TargetGroupStickinessConfig": {
                                "Enabled": false
                            }
                        }
                    }
                ]
            }
        ]
    }

For more information, see `Create an HTTPS listener for your Application Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/create-https-listener.html>`__ in the *Application Load Balancers Guide*.

**Example 3: To create a TCP listener**

The following ``create-listener`` example creates a TCP listener for the specified Network Load Balancer that forwards requests to the specified target group. ::

    aws elbv2 create-listener \
        --load-balancer-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/net/my-network-load-balancer/5d1b75f4f1cee11e \
        --protocol TCP \
        --port 80 \
        --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-tcp-targets/b6bba954d1361c78

Output::

    {
        "Listeners": [
            {
                "ListenerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:listener/net/my-network-load-balancer/5d1b75f4f1cee11e/1a2b3c4d5e6f7a8b",
                "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/net/my-network-load-balancer/5d1b75f4f1cee11e",
                "Port": 80,
                "Protocol": "TCP",
                "DefaultActions": [
                    {
                        "Type": "forward",
                        "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-tcp-targets/b6bba954d1361c78",
                        "ForwardConfig": {
                            "TargetGroups": [
                                {
                                    "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-tcp-targets/b6bba954d1361c78",
                                    "Weight": 1
                                }
                            ],
                            "TargetGroupStickinessConfig": {
                                "Enabled": false
                            }
                        }
                    }
                ]
            }
        ]
    }

For more information, see `Create a listener for your Network Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/network/create-listener.html>`__ in the *Network Load Balancers Guide*.

**Example 4: To create a TLS listener**

The following ``create-listener`` example creates a TLS listener for the specified Network Load Balancer that forwards requests to the specified target group. You must specify an SSL certificate for a TLS listener. ::

    aws elbv2 create-listener \
        --load-balancer-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188 \
        --protocol TLS \
        --port 443 \
        --certificates CertificateArn=arn:aws:acm:us-west-2:123456789012:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --ssl-policy ELBSecurityPolicy-2016-08 \
        --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067

Output::

    {
        "Listeners": [
            {
                "ListenerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:listener/app/my-load-balancer/50dc6c495c0c9188/2b3c4d5e6f7a8b9c",
                "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188",
                "Port": 443,
                "Protocol": "TLS",
                "Certificates": [
                    {
                        "CertificateArn": "arn:aws:acm:us-west-2:123456789012:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
                    }
                ],
                "SslPolicy": "ELBSecurityPolicy-2016-08",
                "DefaultActions": [
                    {
                        "Type": "forward",
                        "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067",
                        "ForwardConfig": {
                            "TargetGroups": [
                                {
                                    "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067",
                                    "Weight": 1
                                }
                            ],
                            "TargetGroupStickinessConfig": {
                                "Enabled": false
                            }
                        }
                    }
                ]
            }
        ]
    }

For more information, see `Server certificates for your Network Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/network/tls-listener-certificates.html>`__ in the *Network Load Balancers Guide*.

**Example 5: To create a UDP listener**

The following ``create-listener`` example creates a UDP listener for the specified Network Load Balancer that forwards requests to the specified target group. ::

    aws elbv2 create-listener \
        --load-balancer-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/net/my-network-load-balancer/5d1b75f4f1cee11e \
        --protocol UDP \
        --port 53 \
        --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-tcp-targets/b6bba954d1361c78

Output::

    {
        "Listeners": [
            {
                "ListenerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:listener/net/my-network-load-balancer/5d1b75f4f1cee11e/3c4d5e6f7a8b9c0d",
                "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/net/my-network-load-balancer/5d1b75f4f1cee11e",
                "Port": 53,
                "Protocol": "UDP",
                "DefaultActions": [
                    {
                        "Type": "forward",
                        "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-tcp-targets/b6bba954d1361c78",
                        "ForwardConfig": {
                            "TargetGroups": [
                                {
                                    "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-tcp-targets/b6bba954d1361c78",
                                    "Weight": 1
                                }
                            ],
                            "TargetGroupStickinessConfig": {
                                "Enabled": false
                            }
                        }
                    }
                ]
            }
        ]
    }

For more information, see `Create a listener for your Network Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/network/create-listener.html>`__ in the *Network Load Balancers Guide*.

**Example 6: To create a listener for the specified gateway and forwarding**

The following ``create-listener`` example creates a listener for the specified Gateway Load Balancer that forwards requests to the specified target group. ::

    aws elbv2 create-listener \
        --load-balancer-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/gwy/my-gateway-load-balancer/e0f9b3d5c7f7d3d6 \
        --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-glb-targets/007ca469fae3bb1615

Output::

    {
        "Listeners": [
            {
                "ListenerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:listener/gwy/my-agw-lb-example2/e0f9b3d5c7f7d3d6/afc127db15f925de",
                "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/gwy/my-agw-lb-example2/e0f9b3d5c7f7d3d6",
                "DefaultActions": [
                    {
                        "Type": "forward",
                        "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/test-tg-agw-2/007ca469fae3bb1615",
                        "ForwardConfig": {
                            "TargetGroups": [
                                {
                                    "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/test-tg-agw-2/007ca469fae3bb1615"
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }

For more information, see `Getting started with Gateway Load Balancers using the AWS CLI <https://docs.aws.amazon.com/elasticloadbalancing/latest/gateway/getting-started-cli.html>`__ in the *Gateway Load Balancers Guide*.