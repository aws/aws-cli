**To disable a CloudWatch Events rule**

The following ``disable-rule`` example disables the rule named ``DailyLambdaFunction``. The rule is not deleted. ::

    aws events disable-rule \
        --name "DailyLambdaFunction"

This command produces no output.

For more information, see `Disabling or deleting a rule in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-delete-rule.html>`__ in the *Amazon EventBridge User Guide*.
