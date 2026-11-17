**Example 1: To test invoke the root resource in an API by making a GET request**

The following ``test-invoke-method`` example tests an invocation of the root resource in an API by making a GET request. ::

    aws apigateway test-invoke-method \
        --rest-api-id 1234123412 \
        --resource-id avl5sg8fw8 \
        --http-method GET \
        --path-with-query-string '/'

Output::

    {
        "status": 200,
        "body": "{\"message\": \"Welcome to the root resource\"}",
        "headers": {
            "Content-Type": "application/json"
        },
        "multiValueHeaders": {
            "Content-Type": [
                "application/json"
            ]
        },
        "log": "Execution log for request a1b2c3d4-5678-90ab-cdef-EXAMPLE11111\nWed Feb 24 00:51:47 UTC 2016 : Starting execution for request: a1b2c3d4-5678-90ab-cdef-EXAMPLE11111\nWed Feb 24 00:51:47 UTC 2016 : HTTP Method: GET, Resource Path: /\nWed Feb 24 00:51:47 UTC 2016 : Method completed with status: 200\n",
        "latency": 45
    }

For more information, see `Use the API Gateway console to test a REST API method <https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-test-method.html>`__ in the *Amazon API Gateway Developer Guide*.

**Example 2: To test invoke a sub-resource in an API by making a GET request with a path parameter value specified**

The following ``test-invoke-method`` example tests an invocation of a sub-resource in an API by making a GET request with a path parameter value specified. ::

    aws apigateway test-invoke-method \
        --rest-api-id 1234123412 \
        --resource-id 3gapai \
        --http-method GET \
        --path-with-query-string '/pets/1'

Output::

    {
        "status": 200,
        "body": "{\"id\": 1, \"type\": \"dog\", \"price\": 249.99}",
        "headers": {
            "Content-Type": "application/json"
        },
        "multiValueHeaders": {
            "Content-Type": [
                "application/json"
            ]
        },
        "log": "Execution log for request a1b2c3d4-5678-90ab-cdef-EXAMPLE22222\nWed Feb 24 00:51:47 UTC 2016 : Starting execution for request: a1b2c3d4-5678-90ab-cdef-EXAMPLE22222\nWed Feb 24 00:51:47 UTC 2016 : HTTP Method: GET, Resource Path: /pets/1\nWed Feb 24 00:51:47 UTC 2016 : Method completed with status: 200\n",
        "latency": 52
    }

For more information, see `Use the API Gateway console to test a REST API method <https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-test-method.html>`__ in the *Amazon API Gateway Developer Guide*.
