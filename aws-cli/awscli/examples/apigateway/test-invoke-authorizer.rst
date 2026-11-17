**To test invoke a request to a Custom Authorizer including the required header and value**

The following ``test-invoke-authorizer`` example tests a request to a Custom Authorizer including the required header and value. ::

    aws apigateway test-invoke-authorizer \
        --rest-api-id 1234123412 \
        --authorizer-id 5yid1t \
        --headers Authorization='Value'

Output::

    {
        "clientStatus": 0,
        "log": "Execution log for request a1b2c3d4-5678-90ab-cdef-EXAMPLE11111\nWed Feb 24 00:51:47 UTC 2016 : Starting authorizer: 5yid1t for request: a1b2c3d4-5678-90ab-cdef-EXAMPLE11111\nWed Feb 24 00:51:47 UTC 2016 : Successfully completed authorizer execution\n",
        "latency": 250,
        "principalId": "user",
        "policy": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Action\":\"execute-api:Invoke\",\"Effect\":\"Allow\",\"Resource\":\"arn:aws:execute-api:us-west-2:123456789012:1234123412/*/GET/\"}]}",
        "authorization": {
            "Authorization": [
                "Value"
            ]
        },
        "claims": {}
    }

For more information, see `Use API Gateway Lambda authorizers <https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-use-lambda-authorizer.html>`__ in the *Amazon API Gateway Developer Guide*.
