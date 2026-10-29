**Example 1: To create a new method response header for the 200 response in a method and define it as not required (default)**

The following ``update-method-response`` example creates a new method response header for the 200 response in a method and defines it as not required (default). ::

    aws apigateway update-method-response \
        --rest-api-id 1234123412 \
        --resource-id a1b2c3 \
        --http-method GET \
        --status-code 200 \
        --patch-operations op="add",path="/responseParameters/method.response.header.custom-header",value="false"

Output::

    {
        "statusCode": "200",
        "responseParameters": {
            "method.response.header.custom-header": false
        },
        "responseModels": {
            "application/json": "Empty"
        }
    }

**Example 2: To delete a response model for the 200 response in a method**

The following ``update-method-response`` example deletes a response model for the 200 response in a method. ::

    aws apigateway update-method-response \
        --rest-api-id 1234123412 \
        --resource-id a1b2c3 \
        --http-method GET \
        --status-code 200 \
        --patch-operations op="remove",path="/responseModels/application~1json"

Output::

    {
        "statusCode": "200"
    }

For more information, see `Set up a method response in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-method-settings-method-response.html>`__ in the *Amazon API Gateway Developer Guide*.
