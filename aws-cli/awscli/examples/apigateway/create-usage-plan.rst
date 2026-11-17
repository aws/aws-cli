**To create a usage plan with throttle and quota limits that resets at the beginning of the month**

The following ``create-usage-plan`` example creates a usage plan with throttle and quota limits that resets at the beginning of the month. ::

    aws apigateway create-usage-plan \
        --name "New Usage Plan" \
        --description "A new usage plan" \
        --throttle burstLimit=10,rateLimit=5 \
        --quota limit=500,offset=0,period=MONTH

Output::

    {
        "id": "a1b2c3",
        "name": "New Usage Plan",
        "description": "A new usage plan",
        "apiStages": [],
        "throttle": {
            "burstLimit": 10,
            "rateLimit": 5.0
        },
        "quota": {
            "limit": 500,
            "offset": 0,
            "period": "MONTH"
        }
    }

For more information, see `Set up usage plans for REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-create-usage-plans.html>`__ in the *Amazon API Gateway Developer Guide*.
