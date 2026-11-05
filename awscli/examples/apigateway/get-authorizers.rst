**To get the list of authorizers for a REST API**

The following ``get-authorizers`` example gets the list of authorizers for a REST API. ::

    aws apigateway get-authorizers \
        --rest-api-id 1234123412

Output::

    {
        "items": [
            {
                "name": "MyAuthorizer",
                "authorizerUri": "arn:aws:apigateway:us-west-2:lambda:path/2015-03-31/functions/arn:aws:lambda:us-west-2:123456789012:function:My_Authorizer_Function/invocations",
                "authorizerResultTtlInSeconds": 300,
                "identitySource": "method.request.header.Authorization",
                "type": "TOKEN",
                "id": "gfi4n3"
            }
        ]
    }

For more information, see `Use API Gateway Lambda authorizers <https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-use-lambda-authorizer.html>`__ in the *Amazon API Gateway Developer Guide*.
