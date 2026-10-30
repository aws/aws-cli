**Example 1: To test invoke the root resource in an API by making a GET request**

The following ``test-invoke-method`` example tests an invocation of the root resource in an API by making a GET request. ::

    aws apigateway test-invoke-method \
        --rest-api-id 1234123412 \
        --resource-id avl5sg8fw8 \
        --http-method GET \
        --path-with-query-string '/'

**Example 2: To test invoke a sub-resource in an API by making a GET request with a path parameter value specified**

The following ``test-invoke-method`` example tests an invocation of a sub-resource in an API by making a GET request with a path parameter value specified. ::

    aws apigateway test-invoke-method \
        --rest-api-id 1234123412 \
        --resource-id 3gapai \
        --http-method GET \
        --path-with-query-string '/pets/1'
