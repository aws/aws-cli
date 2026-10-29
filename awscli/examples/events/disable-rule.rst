**To disable a CloudWatch Events rule**

The following ``disable-rule`` example disables the rule named ``DailyLambdaFunction``. The rule is not deleted. ::

    aws events disable-rule \
        --name "DailyLambdaFunction"

This command produces no output.
