**Example 1: To create an API**

The following ``create-rest-api`` example creates an API named ``My First API``. ::

    aws apigateway create-rest-api \
        --name 'My First API' \
        --description 'This is my first API'

Output::

    {
        "id": "1234123412",
        "name": "My First API",
        "description": "This is my first API",
        "createdDate": "2022-07-18T10:11:18-07:00",
        "apiKeySource": "HEADER",
        "endpointConfiguration": {
            "types": [
                "EDGE"
            ]
        },
        "disableExecuteApiEndpoint": false,
        "rootResourceId": "a1b2c3d4e5"
    }

**Example 2: To create a duplicate API from an existing API**

The following ``create-rest-api`` example creates a duplicate of an existing API by cloning it. ::

    aws apigateway create-rest-api \
        --name 'Copy of My First API' \
        --description 'This is a copy of my first API' \
        --clone-from 1234123412

Output::

    {
        "id": "5678567856",
        "name": "Copy of My First API",
        "description": "This is a copy of my first API",
        "createdDate": "2022-07-18T10:19:04-07:00",
        "apiKeySource": "HEADER",
        "endpointConfiguration": {
            "types": [
                "EDGE"
            ]
        },
        "disableExecuteApiEndpoint": false,
        "rootResourceId": "f6g7h8i9j0"
    }

For more information, see `Develop REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/rest-api-develop.html>`__ in the *Amazon API Gateway Developer Guide*.
