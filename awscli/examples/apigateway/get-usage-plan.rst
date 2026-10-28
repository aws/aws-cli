**To get the details of a Usage Plan**

The following ``get-usage-plan`` example gets the details of the specified usage plan. ::

    aws apigateway get-usage-plan \
        --usage-plan-id a1b2c3

Output::

    {
        "id": "a1b2c3",
        "name": "MyUsagePlan",
        "description": "My usage plan",
        "apiStages": [
            {
                "apiId": "1234123412",
                "stage": "dev"
            }
        ],
        "throttle": {
            "burstLimit": 100,
            "rateLimit": 50.0
        },
        "quota": {
            "limit": 5000,
            "offset": 0,
            "period": "MONTH"
        }
    }
