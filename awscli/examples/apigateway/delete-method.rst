**To delete a method for the given resource in an API**

The following ``delete-method`` example deletes a method for the given resource in an API. ::

    aws apigateway delete-method \
        --rest-api-id 1234123412 \
        --resource-id a1b2c3 \
        --http-method GET

This command produces no output.

For more information, see `Methods for REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-method-settings.html>`__ in the *Amazon API Gateway Developer Guide*.
