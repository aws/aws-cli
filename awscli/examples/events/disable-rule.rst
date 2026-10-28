**To disable a CloudWatch Events rule**

The following ``disable-rule`` example disables the rule named ``DailyLambdaFunction``. The rule is not deleted. This command produces no output. ::

    aws events disable-rule \
        --name "DailyLambdaFunction"
