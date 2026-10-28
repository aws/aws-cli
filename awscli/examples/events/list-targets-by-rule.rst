**To display all the targets for a CloudWatch Events rule**

The following ``list-targets-by-rule`` example displays all the targets of the rule named ``DailyLambdaFunction``. ::

    aws events list-targets-by-rule \
        --rule "DailyLambdaFunction"
