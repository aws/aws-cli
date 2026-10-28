**To display all the rules that have a specified target**

The following ``list-rule-names-by-target`` example displays all rules that have the Lambda function named ``MyFunctionName`` as the target. ::

    aws events list-rule-names-by-target \
        --target-arn "arn:aws:lambda:us-east-1:123456789012:function:MyFunctionName"

Output::

    {
        "RuleNames": [
            "DailyLambdaFunction"
        ]
    }
