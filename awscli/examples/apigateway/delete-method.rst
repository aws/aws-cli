**To delete a method for the given resource in an API**

The following ``delete-method`` example deletes a method for the given resource in an API. ::

    aws apigateway delete-method \
        --rest-api-id 1234123412 \
        --resource-id a1b2c3 \
        --http-method GET

This command produces no output.
