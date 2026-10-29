**To replace a budget for a Cost and Usage budget**

The following ``update-budget`` example replaces a Cost and Usage budget with a new budget. ::

    aws budgets update-budget \
        --account-id 123456789012 \
        --new-budget file://new-budget.json

Contents of ``new-budget.json``::

    {
        "BudgetLimit": {
            "Amount": "100",
            "Unit": "USD"
        },
        "BudgetName": "Example Budget",
        "BudgetType": "COST",
        "CostFilters": {
            "AZ": [
                "us-west-2"
            ]
        },
        "CostTypes": {
            "IncludeCredit": false,
            "IncludeDiscount": true,
            "IncludeOtherSubscription": true,
            "IncludeRecurring": true,
            "IncludeRefund": true,
            "IncludeSubscription": true,
            "IncludeSupport": true,
            "IncludeTax": true,
            "IncludeUpfront": true,
            "UseBlended": false,
            "UseAmortized": true
        },
        "TimePeriod": {
            "Start": 1477958399,
            "End": 3706473600
        },
        "TimeUnit": "MONTHLY"
    }

This command produces no output.

For more information, see `Editing a budget <https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-edit.html>`__ in the *AWS Cost Management User Guide*.
