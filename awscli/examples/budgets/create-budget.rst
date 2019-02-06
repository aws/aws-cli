**To create a Cost and Usage budget**

This example creates a Cost and Usage budget.

Command::

  aws budgets create-budget --account-id 111122223333 --budget file://budget.json --notifications-with-subscribers file://notifications-with-subscribers.json

budget.json::
  
   {
      "BudgetLimit": {
         "Amount": "100",
         "Unit": "USD"
      },
      "BudgetName": "Example Budget",
      "BudgetType": "COST",
      "CostFilters": {
         "AZ" : [ "us-east-1" ]
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

notifications-with-subscribers.json::

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
