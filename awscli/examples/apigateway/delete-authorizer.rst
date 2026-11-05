**To delete a Custom Authorizer in an API**

The following ``delete-authorizer`` example deletes a custom authorizer in an API. ::

    aws apigateway delete-authorizer \
        --rest-api-id 1234123412 \
        --authorizer-id 7gkfbo

This command produces no output.

For more information, see `Use API Gateway Lambda authorizers <https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-use-lambda-authorizer.html>`__ in the *Amazon API Gateway Developer Guide*.
