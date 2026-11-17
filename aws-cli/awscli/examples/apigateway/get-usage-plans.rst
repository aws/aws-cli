**To get the details of all Usage Plans**

The following ``get-usage-plans`` example gets the details of all usage plans. ::

    aws apigateway get-usage-plans

Output::

    {
        "items": [
            {
                "id": "a1b2c3",
                "name": "My Usage Plan",
                "description": "A sample usage plan",
                "apiStages": [
                    {
                        "apiId": "1234123412",
                        "stage": "Prod"
                    }
                ],
                "throttle": {
                    "burstLimit": 10,
                    "rateLimit": 5.0
                },
                "quota": {
                    "limit": 500,
                    "offset": 0,
                    "period": "MONTH"
                },
                "tags": {}
            }
        ]
    }

For more information, see `Set up usage plans for REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-create-usage-plans.html>`__ in the *Amazon API Gateway Developer Guide*.
