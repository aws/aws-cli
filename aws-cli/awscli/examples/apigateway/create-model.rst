**To create a model for an API**

The following ``create-model`` example creates a model named ``firstModel`` for the specified API. ::

    aws apigateway create-model \
        --rest-api-id 1234123412 \
        --name 'firstModel' \
        --description 'The First Model' \
        --content-type 'application/json' \
        --schema '{ "$schema": "http://json-schema.org/draft-04/schema#", "title": "firstModel", "type": "object", "properties": { "firstProperty" : { "type": "object", "properties": { "key": { "type": "string" } } } } }'

Output::

    {
        "contentType": "application/json",
        "description": "The First Model",
        "name": "firstModel",
        "id": "2rzg0l",
        "schema": "{ \"$schema\": \"http://json-schema.org/draft-04/schema#\", \"title\": \"firstModel\", \"type\": \"object\", \"properties\": { \"firstProperty\" : { \"type\": \"object\", \"properties\": { \"key\": { \"type\": \"string\" } } } } }"
    }

For more information, see `Data models for REST APIs <https://docs.aws.amazon.com/apigateway/latest/developerguide/models-mappings-models.html>`__ in the *Amazon API Gateway Developer Guide*.
