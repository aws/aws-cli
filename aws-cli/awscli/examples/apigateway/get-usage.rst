**To get the usage details for a Usage Plan**

The following ``get-usage`` example gets the usage details for the specified usage plan between 2016-08-16 and 2016-08-17. ::

    aws apigateway get-usage \
        --usage-plan-id a1b2c3 \
        --start-date "2016-08-16" \
        --end-date "2016-08-17"

Output::

    {
        "usagePlanId": "a1b2c3",
        "startDate": "2016-08-16",
        "endDate": "2016-08-17",
        "items": {
            "a1b2c3d4e5f6g7h8i9j0": [
                [
                    13,
                    487
                ],
                [
                    7,
                    480
                ]
            ]
        }
    }

For more information, see `Set up usage plans for REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-create-usage-plans.html>`__ in the *Amazon API Gateway Developer Guide*.
