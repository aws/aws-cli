**To retrieve the notifications for a budget**

The following ``describe-notifications-for-budget`` example retrieves the notifications for a Cost and Usage budget. ::

    aws budgets describe-notifications-for-budget \
        --account-id 123456789012 \
        --budget-name "Example Budget" \
        --max-results 5

Output::

    {
        "Notifications": [
            {
                "Threshold": 80.0,
                "ComparisonOperator": "GREATER_THAN",
                "NotificationType": "ACTUAL"
            }
        ]
    }

For more information, see `Viewing your budgets <https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-view.html>`__ in the *AWS Cost Management User Guide*.
