**To delete a subscriber from a notification**

The following ``delete-subscriber`` example deletes the specified subscriber from the specified notification. ::

    aws budgets delete-subscriber \
        --account-id 111122223333 \
        --budget-name "Example Budget" \
        --notification NotificationType=ACTUAL,ComparisonOperator=GREATER_THAN,Threshold=80,ThresholdType=PERCENTAGE \
        --subscriber SubscriptionType=EMAIL,Address=example@example.com

This command produces no output.

