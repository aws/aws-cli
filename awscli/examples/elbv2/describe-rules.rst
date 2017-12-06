**To describe a rule**

This example describes the specified rule.

Command::

  aws elbv2 describe-rules --rule-arns arn:aws:elasticloadbalancing:us-west-2:123456789012:listener-rule/app/my-load-balancer/50dc6c495c0c9188/f2f7dc8efc522ab2/9683b2d02a6cabee

Output::

  {
    "Rules": [
        {
            "Priority": "10",
            "Conditions": [
                {
                    "Field": "path-pattern",
                    "Values": [
                        "/img/*"
                    ]
                }
            ],
            "RuleArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:listener-rule/app/my-load-balancer/50dc6c495c0c9188/f2f7dc8efc522ab2/9683b2d02a6cabee",
            "IsDefault": false,
            "Actions": [
                {
                    "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets-2/113872332242cd5b",
                    "Type": "forward"
                }
            ]
        }
    ]
  }

**To describe the rules for a listener**

This example describes the rules for the specified listener. The output includes the default rule and any other rules that you've defined.

Command::

  aws elbv2 describe-rules --listener-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:listener/app/my-load-balancer/50dc6c495c0c9188/f2f7dc8efc522ab2

Output::

  {
    "Rules": [
        {
            "Priority": "5",
            "IsDefault": false,
            "Actions": [
                {
                    "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets-1/b6bba954d1361c78",
                    "Type": "forward"
                }
            ],
            "RuleArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:listener-rule/app/my-load-balancer/50dc6c495c0c9188/f2f7dc8efc522ab2/db8b4ff9007785e9",
            "Conditions": [
                {
                    "Field": "host-header",
                    "Values": [
                        "*.example.com"
                    ]
                }
            ]
        },
        {
            "Priority": "10",
            "IsDefault": false,
            "Actions": [
                {
                    "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets-2/113872332242cd5b",
                    "Type": "forward"
                }
            ],
            "RuleArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:listener-rule/app/my-load-balancer/50dc6c495c0c9188/f2f7dc8efc522ab2/9683b2d02a6cabee",
            "Conditions": [
                {
                    "Field": "path-pattern",
                    "Values": [
                        "/img/*"
                    ]
                }
            ]
        },
        {
            "Priority": "default",
            "IsDefault": true,
            "Actions": [
                {
                    "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-default-targets/a8173c00fbbe7b8d",
                    "Type": "forward"
                }
            ],
            "RuleArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:listener-rule/app/my-load-balancer/50dc6c495c0c9188/f2f7dc8efc522ab2/fd906cf3d7a9d36d",
            "Conditions": []
        }
    ]
  }
