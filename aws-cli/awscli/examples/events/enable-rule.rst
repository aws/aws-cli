**To enable a CloudWatch Events rule**

The following ``enable-rule`` example enables the rule named ``DailyLambdaFunction``, which had been previously disabled. ::

    aws events enable-rule \
        --name "DailyLambdaFunction"

This command produces no output.

For more information, see `Rules in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rules.html>`__ in the *Amazon EventBridge User Guide*.
