**To retrieve a budget associated with an account**

The following ``describe-budget`` example retrieves the specified Cost and Usage budget. ::

    aws budgets describe-budget \
        --account-id 123456789012 \
        --budget-name "Example Budget"

Output::

    {
        "Budget": {
            "CalculatedSpend": {
                "ForecastedSpend": {
                    "Amount": "2641.54800000000022919266484677791595458984375",
                    "Unit": "USD"
                },
                "ActualSpend": {
                    "Amount": "604.4560000000000172803993336856365203857421875",
                    "Unit": "USD"
                }
            },
            "BudgetType": "COST",
            "BudgetLimit": {
                "Amount": "100",
                "Unit": "USD"
            },
            "BudgetName": "Example Budget",
            "CostTypes": {
                "IncludeOtherSubscription": true,
                "IncludeUpfront": true,
                "IncludeRefund": true,
                "UseBlended": false,
                "IncludeDiscount": true,
                "UseAmortized": false,
                "IncludeTax": true,
                "IncludeCredit": true,
                "IncludeSupport": true,
                "IncludeRecurring": true,
                "IncludeSubscription": true
            },
            "TimeUnit": "MONTHLY",
            "TimePeriod": {
                "Start": 1477958399.0,
                "End": 3706473600.0
            },
            "CostFilters": {
                "AZ": [
                    "us-west-2"
                ]
            }
        }
    }

For more information, see `Viewing your budgets <https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-view.html>`__ in the *AWS Cost Management User Guide*.
