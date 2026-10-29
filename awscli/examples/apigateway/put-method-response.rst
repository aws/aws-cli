**To create a method response under the specified status code with a custom method response header**

The following ``put-method-response`` example creates a method response under the specified status code with a custom method response header. ::

    aws apigateway put-method-response \
        --rest-api-id 1234123412 \
        --resource-id a1b2c3 \
        --http-method GET \
        --status-code 400 \
        --response-parameters "method.response.header.custom-header=false"

Output::

    {
        "statusCode": "400",
        "responseParameters": {
            "method.response.header.custom-header": false
        }
    }

For more information, see `Set up a method response in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-method-settings-method-response.html>`__ in the *Amazon API Gateway Developer Guide*.
