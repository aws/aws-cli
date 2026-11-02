**To delete a method response for the given resource, method, and status code in an API**

The following ``delete-method-response`` example deletes a method response for the given resource, method, and status code in an API. ::

    aws apigateway delete-method-response \
        --rest-api-id 1234123412 \
        --resource-id a1b2c3 \
        --http-method GET \
        --status-code 200

This command produces no output.

For more information, see `Set up a method response in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-method-settings-method-response.html>`__ in the *Amazon API Gateway Developer Guide*.
