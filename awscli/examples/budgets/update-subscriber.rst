**To replace a subscriber for a Cost and Usage budget**

The following ``update-subscriber`` example replaces the subscriber for a Cost and Usage budget. ::

    aws budgets update-subscriber \
        --account-id 111122223333 \
        --budget-name "Example Budget" \
        --notification NotificationType=ACTUAL,ComparisonOperator=GREATER_THAN,Threshold=80,ThresholdType=PERCENTAGE \
        --old-subscriber SubscriptionType=EMAIL,Address=example@example.com \
        --new-subscriber SubscriptionType=EMAIL,Address=example2@example.com
