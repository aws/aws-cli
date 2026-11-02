**To retrieve the subscribers for a budget notification**

The following ``describe-subscribers-for-notification`` example retrieves the subscribers for a Cost and Usage budget notification. ::

    aws budgets describe-subscribers-for-notification \
        --account-id 123456789012 \
        --budget-name "Example Budget" \
        --notification NotificationType=ACTUAL,ComparisonOperator=GREATER_THAN,Threshold=80,ThresholdType=PERCENTAGE \
        --max-results 5

Output::

    {
        "Subscribers": [
            {
                "SubscriptionType": "EMAIL",
                "Address": "example2@example.com"
            },
            {
                "SubscriptionType": "EMAIL",
                "Address": "example@example.com"
            }
        ]
    }

For more information, see `Viewing your budgets <https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-view.html>`__ in the *AWS Cost Management User Guide*.
