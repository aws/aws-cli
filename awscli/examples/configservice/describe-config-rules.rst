**To get details for an AWS Config rule**

The following ``describe-config-rules`` example returns details for an AWS Config rule named ``InstanceTypesAreT2micro``. ::

    aws configservice describe-config-rules \
        --config-rule-names InstanceTypesAreT2micro

Output::

    {
        "ConfigRules": [
            {
                "ConfigRuleState": "ACTIVE",
                "Description": "Evaluates whether EC2 instances are the t2.micro type.",
                "ConfigRuleName": "InstanceTypesAreT2micro",
                "ConfigRuleArn": "arn:aws:config:us-west-2:123456789012:config-rule/config-rule-abcdef",
                "Source": {
                    "Owner": "CUSTOM_LAMBDA",
                    "SourceIdentifier": "arn:aws:lambda:us-west-2:123456789012:function:InstanceTypeCheck",
                    "SourceDetails": [
                        {
                            "EventSource": "aws.config",
                            "MessageType": "ConfigurationItemChangeNotification"
                        }
                    ]
                },
                "InputParameters": "{\"desiredInstanceType\":\"t2.micro\"}",
                "Scope": {
                    "ComplianceResourceTypes": [
                        "AWS::EC2::Instance"
                    ]
                },
                "ConfigRuleId": "config-rule-abcdef"
            }
        ]
    }

For more information, see `Components of an AWS Config Rule <https://docs.aws.amazon.com/config/latest/developerguide/evaluate-config_components.html>`__ in the *AWS Config Developer Guide*.
