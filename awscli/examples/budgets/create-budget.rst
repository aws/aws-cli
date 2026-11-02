**To create a Cost and Usage budget**

The following ``create-budget`` example creates a Cost and Usage budget. ::

    aws budgets create-budget \
        --account-id 123456789012 \
        --budget file://budget.json \
        --notifications-with-subscribers file://notifications-with-subscribers.json
        
Contents of ``budget.json``::

    {
        "BudgetLimit": {
            "Amount": "100",
            "Unit": "USD"
        },
        "BudgetName": "Example Tag Budget",
        "BudgetType": "COST",
        "CostFilters": {
            "TagKeyValue": [
                "user:Key$value1",
                "user:Key$value2"
            ]
        },
        "CostTypes": {
            "IncludeCredit": true,
            "IncludeDiscount": true,
            "IncludeOtherSubscription": true,
            "IncludeRecurring": true,
            "IncludeRefund": true,
            "IncludeSubscription": true,
            "IncludeSupport": true,
            "IncludeTax": true,
            "IncludeUpfront": true,
            "UseBlended": false
        },
        "TimePeriod": {
            "Start": 1477958399,
            "End": 3706473600
        },
        "TimeUnit": "MONTHLY"
    }

This command produces no output.

Contents of ``notifications-with-subscribers.json``::

    [
        {
            "Notification": {
                "ComparisonOperator": "GREATER_THAN",
                "NotificationType": "ACTUAL",
                "Threshold": 80,
                "ThresholdType": "PERCENTAGE"
            },
            "Subscribers": [
                {
                    "Address": "example@example.com",
                    "SubscriptionType": "EMAIL"
                }
            ]
        }
    ]

For more information, see `Creating a budget <https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-create.html>`__ in the *AWS Cost Management User Guide*.
