**Example 1: To change the name of the Custom Authorizer**

The following ``update-authorizer`` example changes the name of the Custom Authorizer. ::

    aws apigateway update-authorizer \
        --rest-api-id 1234123412 \
        --authorizer-id gfi4n3 \
        --patch-operations op='replace',path='/name',value='testAuthorizer'

Output::

    {
        "authType": "custom",
        "name": "testAuthorizer",
        "authorizerUri": "arn:aws:apigateway:us-west-2:lambda:path/2015-03-31/functions/arn:aws:lambda:us-west-2:123456789012:function:customAuthorizer/invocations",
        "authorizerResultTtlInSeconds": 300,
        "identitySource": "method.request.header.Authorization",
        "type": "TOKEN",
        "id": "gfi4n3"
    }

For more information, see `Use API Gateway Lambda authorizers <https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-use-lambda-authorizer.html>`__ in the *Amazon API Gateway Developer Guide*.

**Example 2: To change the Lambda Function that is invoked by the Custom Authorizer**

The following ``update-authorizer`` example changes the Lambda Function that is invoked by the Custom Authorizer. ::

    aws apigateway update-authorizer \
        --rest-api-id 1234123412 \
        --authorizer-id gfi4n3 \
        --patch-operations op='replace',path='/authorizerUri',value='arn:aws:apigateway:us-west-2:lambda:path/2015-03-31/functions/arn:aws:lambda:us-west-2:123456789012:function:newAuthorizer/invocations'

Output::

    {
        "authType": "custom",
        "name": "testAuthorizer",
        "authorizerUri": "arn:aws:apigateway:us-west-2:lambda:path/2015-03-31/functions/arn:aws:lambda:us-west-2:123456789012:function:newAuthorizer/invocations",
        "authorizerResultTtlInSeconds": 300,
        "identitySource": "method.request.header.Authorization",
        "type": "TOKEN",
        "id": "gfi4n3"
    }

For more information, see `Use API Gateway Lambda authorizers <https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-use-lambda-authorizer.html>`__ in the *Amazon API Gateway Developer Guide*.
