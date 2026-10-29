**Example 1: To overwrite an existing API using a Swagger template**

The following ``put-rest-api`` example overwrites an existing API using a Swagger template. ::

    aws apigateway put-rest-api \
        --rest-api-id 1234123412 \
        --mode overwrite \
        --body 'fileb:///path/to/API_Swagger_template.json'

Output::

    {
        "id": "1234123412",
        "name": "MyAPI",
        "description": "API defined by a Swagger template",
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

For more information, see `Import an OpenAPI file to update an existing API definition <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-import-api-update.html>`__ in the *Amazon API Gateway Developer Guide*.

**Example 2: To merge a Swagger template into an existing API**

The following ``put-rest-api`` example merges a Swagger template into an existing API. ::

    aws apigateway put-rest-api \
        --rest-api-id 1234123412 \
        --mode merge \
        --body 'fileb:///path/to/API_Swagger_template.json'

Output::

    {
        "id": "1234123412",
        "name": "MyAPI",
        "description": "API defined by a Swagger template",
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

For more information, see `Import an OpenAPI file to update an existing API definition <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-import-api-update.html>`__ in the *Amazon API Gateway Developer Guide*.
