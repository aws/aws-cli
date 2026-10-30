**To get a list of resources for a REST API**

The following ``get-resources`` example gets a list of resources for the specified REST API. ::

    aws apigateway get-resources --rest-api-id 1234123412

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
