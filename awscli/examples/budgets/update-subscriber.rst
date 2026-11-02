**To replace a subscriber for a Cost and Usage budget**

The following ``update-subscriber`` example replaces the subscriber for a Cost and Usage budget. ::

    aws budgets update-subscriber \
        --account-id 123456789012 \
        --budget-name "Example Budget" \
        --notification NotificationType=ACTUAL,ComparisonOperator=GREATER_THAN,Threshold=80,ThresholdType=PERCENTAGE \
        --old-subscriber SubscriptionType=EMAIL,Address=example@example.com \
        --new-subscriber SubscriptionType=EMAIL,Address=example2@example.com

This command produces no output.

For more information, see `Editing a budget <https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-edit.html>`__ in the *AWS Cost Management User Guide*.
