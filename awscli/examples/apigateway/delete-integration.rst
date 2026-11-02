**To delete an integration for a given resource and method in an API**

The following ``delete-integration`` example deletes an integration for a given resource and method in an API. ::

    aws apigateway delete-integration \
        --rest-api-id 1234123412 \
        --resource-id a1b2c3 \
        --http-method GET

This command produces no output.

For more information, see `Integrations for REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-integration-settings.html>`__ in the *Amazon API Gateway Developer Guide*.
