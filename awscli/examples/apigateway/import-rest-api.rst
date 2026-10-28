**To import a Swagger template and create an API**

The following ``import-rest-api`` example imports a Swagger template and creates an API. ::

    aws apigateway import-rest-api \
        --body 'fileb:///path/to/API_Swagger_template.json'

Output::

    {
        "id": "a1b2c3d4e5",
        "name": "MyAPI",
        "description": "API imported from a Swagger template",
        "createdDate": "2016-02-23T23:39:00+00:00",
        "version": "1.0",
        "apiKeySource": "HEADER",
        "endpointConfiguration": {
            "types": [
                "EDGE"
            ]
        },
        "disableExecuteApiEndpoint": false,
        "rootResourceId": "a1b2c3d4f5"
    }
