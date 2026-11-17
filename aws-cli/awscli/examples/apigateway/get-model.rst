**To get the configuration for a model defined under a REST API**

The following ``get-model`` example gets the configuration for the ``Empty`` model defined under a REST API. ::

    aws apigateway get-model \
        --rest-api-id 1234123412 \
        --model-name Empty

Output::

    {
        "contentType": "application/json",
        "description": "This is a default empty schema model",
        "name": "Empty",
        "id": "etd5w5",
        "schema": "{\n  \"$schema\": \"http://json-schema.org/draft-04/schema#\",\n  \"title\" : \"Empty Schema\",\n  \"type\" : \"object\"\n}"
    }

For more information, see `Data models for REST APIs <https://docs.aws.amazon.com/apigateway/latest/developerguide/models-mappings-models.html>`__ in the *Amazon API Gateway Developer Guide*.
