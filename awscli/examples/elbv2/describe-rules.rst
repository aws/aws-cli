**Example 1: To describe a rule**

The following ``describe-rules`` example displays details for the specified rule. ::

    aws elbv2 describe-rules \
        --rule-arns arn:aws:elasticloadbalancing:us-west-2:123456789012:listener-rule/app/my-load-balancer/50dc6c495c0c9188/f2f7dc8efc522ab2/9683b2d02a6cabee

Output::

    {
        "Rules": [
            {
                "RuleArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:listener-rule/app/my-load-balancer/50dc6c495c0c9188/f2f7dc8efc522ab2/9683b2d02a6cabee",
                "Priority": "10",
                "Conditions": [
                    {
                        "Field": "path-pattern",
                        "Values": [
                            "/img/*"
                        ],
                        "PathPatternConfig": {
                            "Values": [
                                "/img/*"
                            ]
                        }
                    }
                ],
                "Actions": [
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
                ],
                "IsDefault": false
            }
        ]
    }

For more information, see `Listener rules for your Application Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/listener-rules.html>`__ in the *Application Load Balancers Guide*.

**Example 2: To describe the rules for a listener**

The following ``describe-rules`` example displays details for the rules for the specified listener. The output includes the default rule and any other rules that you've added. ::

    aws elbv2 describe-rules \
        --listener-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:listener/app/my-load-balancer/50dc6c495c0c9188/f2f7dc8efc522ab2

Output::

    {
        "Rules": [
            {
                "RuleArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:listener-rule/app/my-load-balancer/50dc6c495c0c9188/f2f7dc8efc522ab2/9683b2d02a6cabee",
                "Priority": "10",
                "Conditions": [
                    {
                        "Field": "path-pattern",
                        "Values": [
                            "/img/*"
                        ],
                        "PathPatternConfig": {
                            "Values": [
                                "/img/*"
                            ]
                        }
                    }
                ],
                "Actions": [
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
                ],
                "IsDefault": false
            },
            {
                "RuleArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:listener-rule/app/my-load-balancer/50dc6c495c0c9188/f2f7dc8efc522ab2/d8a7a5fbe2f8d8d4",
                "Priority": "default",
                "Conditions": [],
                "Actions": [
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
                ],
                "IsDefault": true
            }
        ]
    }

For more information, see `Listener rules for your Application Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/listener-rules.html>`__ in the *Application Load Balancers Guide*.
