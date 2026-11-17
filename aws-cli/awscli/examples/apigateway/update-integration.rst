**Example 1: To add the 'Content-Type: application/json' Mapping Template configured with Input Passthrough**

The following ``update-integration`` example adds the 'Content-Type: application/json' Mapping Template configured with Input Passthrough. ::

    aws apigateway update-integration \
        --rest-api-id a1b2c3d4e5 \
        --resource-id a1b2c3 \
        --http-method POST \
        --patch-operations "op='add',path='/requestTemplates/application~1json'"

Output::

    {
        "type": "MOCK",
        "requestTemplates": {
            "application/json": null
        },
        "passthroughBehavior": "WHEN_NO_MATCH",
        "timeoutInMillis": 29000,
        "cacheNamespace": "a1b2c3",
        "cacheKeyParameters": []
    }

**Example 2: To update (replace) the 'Content-Type: application/json' Mapping Template configured with a custom template**

The following ``update-integration`` example updates (replaces) the 'Content-Type: application/json' Mapping Template configured with a custom template. ::

    aws apigateway update-integration \
        --rest-api-id a1b2c3d4e5 \
        --resource-id a1b2c3 \
        --http-method POST \
        --patch-operations "op='replace',path='/requestTemplates/application~1json',value='{"example": "json"}'"

Output::

    {
        "type": "MOCK",
        "requestTemplates": {
            "application/json": "{\"example\": \"json\"}"
        },
        "passthroughBehavior": "WHEN_NO_MATCH",
        "timeoutInMillis": 29000,
        "cacheNamespace": "a1b2c3",
        "cacheKeyParameters": []
    }

**Example 3: To update (replace) a custom template associated with 'Content-Type: application/json' with Input Passthrough**

The following ``update-integration`` example updates (replaces) a custom template associated with 'Content-Type: application/json' with Input Passthrough. ::

    aws apigateway update-integration \
        --rest-api-id a1b2c3d4e5 \
        --resource-id a1b2c3 \
        --http-method POST \
        --patch-operations "op='replace',path='requestTemplates/application~1json'"

Output::

    {
        "type": "MOCK",
        "requestTemplates": {
            "application/json": null
        },
        "passthroughBehavior": "WHEN_NO_MATCH",
        "timeoutInMillis": 29000,
        "cacheNamespace": "a1b2c3",
        "cacheKeyParameters": []
    }

**Example 4: To remove the 'Content-Type: application/json' Mapping Template**

The following ``update-integration`` example removes the 'Content-Type: application/json' Mapping Template. ::

    aws apigateway update-integration \
        --rest-api-id a1b2c3d4e5 \
        --resource-id a1b2c3 \
        --http-method POST \
        --patch-operations "op='remove',path='/requestTemplates/application~1json'"

Output::

    {
        "type": "MOCK",
        "passthroughBehavior": "WHEN_NO_MATCH",
        "timeoutInMillis": 29000,
        "cacheNamespace": "a1b2c3",
        "cacheKeyParameters": []
    }

For more information, see `Mapping template transformations for REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/models-mappings.html>`__ in the *Amazon API Gateway Developer Guide*.
