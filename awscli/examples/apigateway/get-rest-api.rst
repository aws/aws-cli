**To get information about an API**

The following ``get-rest-api`` example gets information about the specified REST API. ::

    aws apigateway get-rest-api \
        --rest-api-id 1234123412

Output::

    {
        "name": "myAPI",
        "id": "o1y243m4f5",
        "createdDate": 1453416433
    }

For more information, see `API Gateway REST APIs <https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-rest-api.html>`__ in the *Amazon API Gateway Developer Guide*.
