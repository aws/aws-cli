**Example 1: To change the name for an API Key**

The following ``update-api-key`` example changes the name for an API Key. ::

    aws apigateway update-api-key \
        --api-key sNvjQDMReA1eEQPNAW8r37XsU2rDD7fc7m2SiMnu \
        --patch-operations op='replace',path='/name',value='newName'

Output::

    {
        "description": "currentDescription",
        "enabled": true,
        "stageKeys": [
            "41t2j324r5/dev"
        ],
        "lastUpdatedDate": 1470086052,
        "createdDate": 1445460347,
        "id": "sNvjQDMReA1vEQPNzW8r3dXsU2rrD7fcjm2SiMnu",
        "name": "newName"
    }

For more information, see `Set up API keys for REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-setup-api-keys.html>`__ in the *Amazon API Gateway Developer Guide*.

**Example 2: To disable the API Key**

The following ``update-api-key`` example disables the API Key. ::

    aws apigateway update-api-key \
        --api-key sNvjQDMReA1eEQPNAW8r37XsU2rDD7fc7m2SiMnu \
        --patch-operations op='replace',path='/enabled',value='false'

Output::

    {
        "description": "currentDescription",
        "enabled": false,
        "stageKeys": [
            "41t2j324r5/dev"
        ],
        "lastUpdatedDate": 1470086052,
        "createdDate": 1445460347,
        "id": "sNvjQDMReA1vEQPNzW8r3dXsU2rrD7fcjm2SiMnu",
        "name": "newName"
    }

For more information, see `Set up API keys for REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-setup-api-keys.html>`__ in the *Amazon API Gateway Developer Guide*.
