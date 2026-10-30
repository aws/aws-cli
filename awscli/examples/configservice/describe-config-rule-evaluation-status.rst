**To get status information for an AWS Config rule**

The following ``describe-config-rule-evaluation-status`` example returns the status information for an AWS Config rule named ``MyConfigRule``. ::

    aws configservice describe-config-rule-evaluation-status \
        --config-rule-names MyConfigRule

Output::

    {
        "ConfigRulesEvaluationStatus": [
            {
                "ConfigRuleArn": "arn:aws:config:us-west-2:123456789012:config-rule/config-rule-abcdef",
                "FirstActivatedTime": 1450311703.844,
                "ConfigRuleId": "config-rule-abcdef",
                "LastSuccessfulInvocationTime": 1450314643.156,
                "ConfigRuleName": "MyConfigRule"
            }
        ]
    }

For more information, see `Evaluating Your Resources with AWS Config Rules <https://docs.aws.amazon.com/config/latest/developerguide/evaluating-your-resources.html>`__ in the *AWS Config Developer Guide*.
