**To delete a notification from a budget**

The following ``delete-notification`` example deletes the specified notification from the specified budget. ::

    aws budgets delete-notification \
        --account-id 111122223333 \
        --budget-name "Example Budget" \
        --notification NotificationType=ACTUAL,ComparisonOperator=GREATER_THAN,Threshold=80,ThresholdType=PERCENTAGE

This command produces no output.

