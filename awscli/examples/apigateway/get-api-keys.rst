**To get the list of API keys**

The following ``get-api-keys`` example gets the list of API keys. ::

    aws apigateway get-api-keys

Output::

    {
        "items": [
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
        ]
    }

For more information, see `Set up API keys for REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-setup-api-keys.html>`__ in the *Amazon API Gateway Developer Guide*.
