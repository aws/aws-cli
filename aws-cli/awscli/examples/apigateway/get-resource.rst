**To get information about a resource**

The following ``get-resource`` example gets information about the specified resource. ::

    aws apigateway get-resource \
        --rest-api-id 1234123412 \
        --resource-id zwo0y3

Output::

    {
        "path": "/path",
        "pathPart": "path",
        "id": "zwo0y3",
        "parentId": "uyokt6ij2g"
    }

For more information, see `Develop REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/rest-api-develop.html>`__ in the *Amazon API Gateway Developer Guide*.
