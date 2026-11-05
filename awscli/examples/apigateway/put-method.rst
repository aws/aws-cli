**To create a method for a resource in an API with no authorization, no API key, and a custom method request header**

The following ``put-method`` example creates a method for a resource in an API with no authorization, no API key, and a custom method request header. ::

    aws apigateway put-method \
        --rest-api-id 1234123412 \
        --resource-id a1b2c3 \
        --http-method PUT \
        --authorization-type "NONE" \
        --no-api-key-required \
        --request-parameters "method.request.header.custom-header=false"

Output::

    {
        "httpMethod": "PUT",
        "authorizationType": "NONE",
        "apiKeyRequired": false,
        "requestParameters": {
            "method.request.header.custom-header": false
        }
    }

For more information, see `Set up a method request in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-method-settings-method-request.html>`__ in the *Amazon API Gateway Developer Guide*.
