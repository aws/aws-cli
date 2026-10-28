**To display information about a CloudWatch Events rule**

The following ``describe-rule`` example displays information about the rule named ``DailyLambdaFunction``. ::

    aws events describe-rule \
        --name "DailyLambdaFunction"
