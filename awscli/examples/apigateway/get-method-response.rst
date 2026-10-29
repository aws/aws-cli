**To get the method response resource configuration for a HTTP method defined under a REST API's resource**

The following ``get-method-response`` example gets the method response resource configuration for the ``200`` status code of the ``GET`` method defined under a REST API's resource. ::

    aws apigateway get-method-response \
        --rest-api-id 1234123412 \
        --resource-id y9h6rt \
        --http-method GET \
        --status-code 200

Output::

    {
        "responseModels": {
            "application/json": "Empty"
        },
        "statusCode": "200"
    }

For more information, see `Set up a method response in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-method-settings-method-response.html>`__ in the *Amazon API Gateway Developer Guide*.
