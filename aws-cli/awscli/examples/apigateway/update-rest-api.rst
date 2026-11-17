**Example 1: To change the name of an API**

The following ``update-rest-api`` example changes the name of an API. ::

    aws apigateway update-rest-api \
        --rest-api-id 1234123412 \
        --patch-operations op=replace,path=/name,value='New Name'

Output::

    {
        "id": "1234123412",
        "name": "New Name",
        "description": "My API description",
        "createdDate": "2022-10-06T15:32:41+00:00",
        "apiKeySource": "HEADER",
        "endpointConfiguration": {
            "types": [
                "EDGE"
            ],
            "ipAddressType": "ipv4"
        },
        "disableExecuteApiEndpoint": false,
        "rootResourceId": "a1b2c3d4e5"
    }

**Example 2: To change the description of an API**

The following ``update-rest-api`` example changes the description of an API. ::

    aws apigateway update-rest-api \
        --rest-api-id 1234123412 \
        --patch-operations op=replace,path=/description,value='New Description'

Output::

    {
        "id": "1234123412",
        "name": "MyAPI",
        "description": "New Description",
        "createdDate": "2022-10-06T15:32:41+00:00",
        "apiKeySource": "HEADER",
        "endpointConfiguration": {
            "types": [
                "EDGE"
            ],
            "ipAddressType": "ipv4"
        },
        "disableExecuteApiEndpoint": false,
        "rootResourceId": "a1b2c3d4e5"
    }

For more information, see `Develop REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/rest-api-develop.html>`__ in the *Amazon API Gateway Developer Guide*.
