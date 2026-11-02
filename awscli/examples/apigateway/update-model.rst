**Example 1: To change the description of a model in an API**

The following ``update-model`` example changes the description of a model in an API. ::

    aws apigateway update-model \
        --rest-api-id 1234123412 \
        --model-name 'Empty' \
        --patch-operations op=replace,path=/description,value='New Description'

Output::

    {
        "id": "a1b2c3",
        "name": "Empty",
        "description": "New Description",
        "schema": "{\n  \"$schema\": \"http://json-schema.org/draft-04/schema#\",\n  \"title\" : \"Empty Schema\",\n  \"type\" : \"object\"\n}",
        "contentType": "application/json"
    }

**Example 2: To change the schema of a model in an API**

The following ``update-model`` example changes the schema of a model in an API. ::

    aws apigateway update-model \
        --rest-api-id 1234123412 \
        --model-name 'Empty' \
        --patch-operations op=replace,path=/schema,value='"{ \"$schema\": \"http://json-schema.org/draft-04/schema#\", \"title\" : \"Empty Schema\", \"type\" : \"object\" }"'

Output::

    {
        "id": "a1b2c3",
        "name": "Empty",
        "description": "This is a default empty schema model",
        "schema": "{ \"$schema\": \"http://json-schema.org/draft-04/schema#\", \"title\" : \"Empty Schema\", \"type\" : \"object\" }",
        "contentType": "application/json"
    }

For more information, see `Data models for REST APIs <https://docs.aws.amazon.com/apigateway/latest/developerguide/models-mappings-models.html>`__ in the *Amazon API Gateway Developer Guide*.
