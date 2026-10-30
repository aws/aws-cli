**To create a resource in an API**

The following ``create-resource`` example creates a resource with the path part ``new-resource`` under the specified parent resource in an API. ::

    aws apigateway create-resource --rest-api-id 1234123412 --parent-id a1b2c3 --path-part 'new-resource'
