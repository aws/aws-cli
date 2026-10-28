**To enable a CloudWatch Events rule**

The following ``enable-rule`` example enables the rule named ``DailyLambdaFunction``, which had been previously disabled. ::

    aws events enable-rule --name "DailyLambdaFunction"
