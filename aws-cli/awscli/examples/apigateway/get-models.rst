**To get a list of models for a REST API**

The following ``get-models`` example gets a list of models for the specified REST API. ::

    aws apigateway get-models \
        --rest-api-id 1234123412

Output::

    {
        "items": [
            {
                "description": "This is a default error schema model",
                "schema": "{\n  \"$schema\" : \"http://json-schema.org/draft-04/schema#\",\n  \"title\" : \"Error Schema\",\n  \"type\" : \"object\",\n  \"properties\" : {\n    \"message\" : { \"type\" : \"string\" }\n  }\n}",
                "contentType": "application/json",
                "id": "7tpbze",
                "name": "Error"
            },
            {
                "description": "This is a default empty schema model",
                "schema": "{\n  \"$schema\": \"http://json-schema.org/draft-04/schema#\",\n  \"title\" : \"Empty Schema\",\n  \"type\" : \"object\"\n}",
                "contentType": "application/json",
                "id": "etd5w5",
                "name": "Empty"
            }
        ]
    }

For more information, see `Data models for REST APIs <https://docs.aws.amazon.com/apigateway/latest/developerguide/models-mappings-models.html>`__ in the *Amazon API Gateway Developer Guide*.
