**To create an API key that is enabled for an existing API and Stage**

The following ``create-api-key`` example creates an API key that is enabled for an existing API and stage. ::

    aws apigateway create-api-key \
        --name 'Dev API Key' \
        --description 'Used for development' \
        --enabled \
        --stage-keys restApiId='a1b2c3d4e5',stageName='dev'

Output::

    {
        "id": "c2b7jkd5ge",
        "value": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6EXAMPLE",
        "name": "Dev API Key",
        "description": "Used for development",
        "enabled": true,
        "createdDate": "2022-07-18T10:11:18-07:00",
        "lastUpdatedDate": "2022-07-18T10:11:18-07:00",
        "stageKeys": [
            "a1b2c3d4e5/dev"
        ]
    }

For more information, see `Set up API keys for REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-setup-api-keys.html>`__ in the *Amazon API Gateway Developer Guide*.
