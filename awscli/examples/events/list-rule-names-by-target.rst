**To display all the rules that have a specified target**

The following ``list-rule-names-by-target`` example displays all rules that have the Lambda function named ``MyFunctionName`` as the target. ::

    aws events list-rule-names-by-target \
        --target-arn "arn:aws:lambda:us-west-2:123456789012:function:MyFunctionName"

Output::

    {
        "RuleNames": [
            "DailyLambdaFunction"
        ]
    }

For more information, see `Event bus targets in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-targets.html>`__ in the *Amazon EventBridge User Guide*.
