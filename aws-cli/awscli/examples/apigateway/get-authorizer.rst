**To get the API Gateway per-API Authorizer settings**

The following ``get-authorizer`` example gets the settings of the specified per-API authorizer. ::

    aws apigateway get-authorizer \
        --rest-api-id 1234123412 \
        --authorizer-id gfi4n3

Output::

    {
        "authorizerResultTtlInSeconds": 300,
        "name": "MyAuthorizer",
        "type": "TOKEN",
        "identitySource": "method.request.header.Authorization",
        "authorizerUri": "arn:aws:apigateway:us-west-2:lambda:path/2015-03-31/functions/arn:aws:lambda:us-west-2:123456789012:function:authorizer_function/invocations",
        "id": "gfi4n3"
    }

For more information, see `Use API Gateway Lambda authorizers <https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-use-lambda-authorizer.html>`__ in the *Amazon API Gateway Developer Guide*.
