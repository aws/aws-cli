**To create a subscriber for a notification associated with a Cost and Usage budget**

The following ``create-subscriber`` example creates a subscriber for the specified notification. ::

    aws budgets create-subscriber \
        --account-id 123456789012 \
        --budget-name "Example Budget" \
        --notification NotificationType=ACTUAL,ComparisonOperator=GREATER_THAN,Threshold=80,ThresholdType=PERCENTAGE \
        --subscriber SubscriptionType=EMAIL,Address=example@example.com

This command produces no output.

For more information, see `Editing a budget <https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-edit.html>`__ in the *AWS Cost Management User Guide*.
