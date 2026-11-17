**To get the information about a specific API key**

The following ``get-api-key`` example gets information about a specific API key. ::

    aws apigateway get-api-key \
        --api-key 8bklk8bl1k3sB38D9B3l0enyWT8c09B30lkq0blk

Output::

    {
        "description": "My first key",
        "enabled": true,
        "stageKeys": [
            "a1b2c3d4e5/dev",
            "e5d4c3b2a1/dev"
        ],
        "lastUpdatedDate": 1456184515,
        "createdDate": 1456184452,
        "id": "8bklk8bl1k3sB38D9B3l0enyWT8c09B30lkq0blk",
        "name": "My key"
    }

For more information, see `Set up API keys for REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-setup-api-keys.html>`__ in the *Amazon API Gateway Developer Guide*.
