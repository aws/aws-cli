**Example 1: To change the period defined in a Usage Plan**

The following ``update-usage-plan`` example changes the period defined in a Usage Plan. ::

    aws apigateway update-usage-plan \
        --usage-plan-id a1b2c3 \
        --patch-operations op="replace",path="/quota/period",value="MONTH"

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

**Example 2: To change the quota limit defined in a Usage Plan**

The following ``update-usage-plan`` example changes the quota limit defined in a Usage Plan. ::

    aws apigateway update-usage-plan \
        --usage-plan-id a1b2c3 \
        --patch-operations op="replace",path="/quota/limit",value="500"

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
            "limit": 500,
            "offset": 0,
            "period": "MONTH"
        }
    }

**Example 3: To change the throttle rate limit defined in a Usage Plan**

The following ``update-usage-plan`` example changes the throttle rate limit defined in a Usage Plan. ::

    aws apigateway update-usage-plan \
        --usage-plan-id a1b2c3 \
        --patch-operations op="replace",path="/throttle/rateLimit",value="10"

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
            "rateLimit": 10.0
        },
        "quota": {
            "limit": 5000,
            "offset": 0,
            "period": "MONTH"
        }
    }

**Example 4: To change the throttle burst limit defined in a Usage Plan**

The following ``update-usage-plan`` example changes the throttle burst limit defined in a Usage Plan. ::

    aws apigateway update-usage-plan \
        --usage-plan-id a1b2c3 \
        --patch-operations op="replace",path="/throttle/burstLimit",value="20"

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
            "burstLimit": 20,
            "rateLimit": 50.0
        },
        "quota": {
            "limit": 5000,
            "offset": 0,
            "period": "MONTH"
        }
    }

For more information, see `Set up usage plans for REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-create-usage-plans.html>`__ in the *Amazon API Gateway Developer Guide*.
