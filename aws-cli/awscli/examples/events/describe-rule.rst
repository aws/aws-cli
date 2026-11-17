**To display information about a CloudWatch Events rule**

The following ``describe-rule`` example displays information about the rule named ``DailyLambdaFunction``. ::

    aws events describe-rule \
        --name "DailyLambdaFunction"

Output::

    {
        "Name": "DailyLambdaFunction",
        "Arn": "arn:aws:events:us-west-2:123456789012:rule/DailyLambdaFunction",
        "ScheduleExpression": "cron(0 9 * * ? *)",
        "State": "ENABLED",
        "EventBusName": "default",
        "CreatedBy": "123456789012"
    }

For more information, see `Rules in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rules.html>`__ in the *Amazon EventBridge User Guide*.
