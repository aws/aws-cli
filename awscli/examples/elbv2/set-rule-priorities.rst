**To set the rule priority**

The following ``set-rule-priorities`` example sets the priority of the specified rule. ::

    aws elbv2 set-rule-priorities \
        --rule-priorities RuleArn=arn:aws:elasticloadbalancing:us-west-2:123456789012:listener-rule/app/my-load-balancer/50dc6c495c0c9188/f2f7dc8efc522ab2/1291d13826f405c3,Priority=5

Output::

    {
        "Rules": [
            {
                "Priority": "5",
                "Conditions": [
                    {
                        "Field": "path-pattern",
                        "Values": [
                            "/img/*"
                        ]
                    }
                ],
                "RuleArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:listener-rule/app/my-load-balancer/50dc6c495c0c9188/f2f7dc8efc522ab2/1291d13826f405c3",
                "IsDefault": false,
                "Actions": [
                    {
                        "TargetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/73e2d6bc24d8a067",
                        "Type": "forward"
                    }
                ]
            }
        ]
    }

For more information, see `Edit a listener rule for your Application Load Balancer <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-rule.html>`__ in the *Application Load Balancers Guide*.
