**To replace a notification for a Cost and Usage budget**

The following ``update-notification`` example replaces an 80% notification for a Cost and Usage budget with a 90% notification. ::

    aws budgets update-notification \
        --account-id 123456789012 \
        --budget-name "Example Budget" \
        --old-notification NotificationType=ACTUAL,ComparisonOperator=GREATER_THAN,Threshold=80,ThresholdType=PERCENTAGE \
        --new-notification NotificationType=ACTUAL,ComparisonOperator=GREATER_THAN,Threshold=90,ThresholdType=PERCENTAGE

This command produces no output.

For more information, see `Editing a budget <https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-edit.html>`__ in the *AWS Cost Management User Guide*.
