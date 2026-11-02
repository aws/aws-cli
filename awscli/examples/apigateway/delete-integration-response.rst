**To delete an integration response for a given resource, method, and status code in an API**

The following ``delete-integration-response`` example deletes an integration response for a given resource, method, and status code in an API. ::

    aws apigateway delete-integration-response \
        --rest-api-id 1234123412 \
        --resource-id a1b2c3 \
        --http-method GET \
        --status-code 200

This command produces no output.

For more information, see `Set up an integration response in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-integration-settings-integration-response.html>`__ in the *Amazon API Gateway Developer Guide*.
