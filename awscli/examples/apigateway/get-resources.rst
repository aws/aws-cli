**To get a list of resources for a REST API**

The following ``get-resources`` example gets a list of resources for the specified REST API. ::

    aws apigateway get-resources \
        --rest-api-id 1234123412

Output::

    {
        "items": [
            {
                "path": "/resource/subresource",
                "resourceMethods": {
                    "POST": {}
                },
                "id": "024ace",
                "pathPart": "subresource",
                "parentId": "ai5b02"
            }
        ]
    }

For more information, see `Develop REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/rest-api-develop.html>`__ in the *Amazon API Gateway Developer Guide*.
