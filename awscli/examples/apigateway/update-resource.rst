**Example 1: To move a resource and place it under a different parent resource in an API**

The following ``update-resource`` example moves a resource and places it under a different parent resource in an API. ::

    aws apigateway update-resource \
        --rest-api-id 1234123412 \
        --resource-id 1a2b3c \
        --patch-operations op=replace,path=/parentId,value='3c2b1a'

Output::

    {
        "path": "/resource",
        "pathPart": "resource",
        "id": "1a2b3c",
        "parentId": "3c2b1a"
    }

**Example 2: To rename a resource (pathPart) in an API**

The following ``update-resource`` example renames a resource (pathPart) in an API. ::

    aws apigateway update-resource \
        --rest-api-id 1234123412 \
        --resource-id 1a2b3c \
        --patch-operations op=replace,path=/pathPart,value=newresourcename

Output::

    {
        "path": "/newresourcename",
        "pathPart": "newresourcename",
        "id": "1a2b3c",
        "parentId": "3c2b1a"
    }

For more information, see `Develop REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/rest-api-develop.html>`__ in the *Amazon API Gateway Developer Guide*.
