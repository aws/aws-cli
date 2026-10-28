**To create a notification for the specified Cost and Usage budget**

The following ``create-notification`` example creates a notification for the specified Cost and Usage budget. This command produces no output. ::

    aws budgets create-notification \
        --account-id 111122223333 \
        --budget-name "Example Budget" \
        --notification NotificationType=ACTUAL,ComparisonOperator=GREATER_THAN,Threshold=80,ThresholdType=PERCENTAGE \
        --subscriber SubscriptionType=EMAIL,Address=example@example.com

