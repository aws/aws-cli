**To display all the targets for a CloudWatch Events rule**

The following ``list-targets-by-rule`` example displays all the targets of the rule named ``DailyLambdaFunction``. ::

    aws events list-targets-by-rule \
        --rule "DailyLambdaFunction"

Output::

    {
        "Targets": [
            {
                "Id": "1",
                "Arn": "arn:aws:lambda:us-west-2:123456789012:function:MyFunctionName"
            }
        ]
    }

For more information, see `Event bus targets in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-targets.html>`__ in the *Amazon EventBridge User Guide*.
