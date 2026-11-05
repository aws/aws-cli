**Example 1: To create a MOCK integration request**

The following ``put-integration`` example creates a MOCK integration request. ::

    aws apigateway put-integration \
        --rest-api-id 1234123412 \
        --resource-id a1b2c3 \
        --http-method GET \
        --type MOCK \
        --request-templates '{ "application/json": "{\"statusCode\": 200}" }'

Output::

    {
        "type": "MOCK",
        "requestTemplates": {
            "application/json": "{\"statusCode\": 200}"
        },
        "passthroughBehavior": "WHEN_NO_MATCH",
        "timeoutInMillis": 29000,
        "cacheNamespace": "a1b2c3",
        "cacheKeyParameters": []
    }

For more information, see `Mock integrations for REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-mock-integration.html>`__ in the *Amazon API Gateway Developer Guide*.

**Example 2: To create a HTTP integration request**

The following ``put-integration`` example creates an HTTP integration request. ::

    aws apigateway put-integration \
        --rest-api-id 1234123412 \
        --resource-id a1b2c3 \
        --http-method GET \
        --type HTTP \
        --integration-http-method GET \
        --uri 'https://domain.tld/path'

Output::

    {
        "type": "HTTP",
        "httpMethod": "GET",
        "uri": "https://domain.tld/path",
        "connectionType": "INTERNET",
        "passthroughBehavior": "WHEN_NO_MATCH",
        "timeoutInMillis": 29000,
        "cacheNamespace": "a1b2c3",
        "cacheKeyParameters": []
    }

For more information, see `HTTP integrations for REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/setup-http-integrations.html>`__ in the *Amazon API Gateway Developer Guide*.

**Example 3: To create an AWS integration request with a Lambda Function endpoint**

The following ``put-integration`` example creates an AWS integration request with a Lambda function endpoint. ::

    aws apigateway put-integration \
        --rest-api-id 1234123412 \
        --resource-id a1b2c3 \
        --http-method GET \
        --type AWS \
        --integration-http-method POST \
        --uri 'arn:aws:apigateway:us-west-2:lambda:path/2015-03-31/functions/arn:aws:lambda:us-west-2:123456789012:function:function_name/invocations'

Output::

    {
        "type": "AWS",
        "httpMethod": "POST",
        "uri": "arn:aws:apigateway:us-west-2:lambda:path/2015-03-31/functions/arn:aws:lambda:us-west-2:123456789012:function:function_name/invocations",
        "passthroughBehavior": "WHEN_NO_MATCH",
        "timeoutInMillis": 29000,
        "cacheNamespace": "a1b2c3",
        "cacheKeyParameters": []
    }

For more information, see `Lambda integrations for REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-integrations.html>`__ in the *Amazon API Gateway Developer Guide*.
