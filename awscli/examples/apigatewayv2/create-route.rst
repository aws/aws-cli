**To create a route for a WebSocket API**

The following ``create-route`` example creates a route for a WebSocket API. ::

    aws apigatewayv2 create-route \
        --api-id aabbccddee \
        --route-key $default

Output::

    {
        "ApiKeyRequired": false,
        "AuthorizationType": "NONE",
        "RouteKey": "$default",
        "RouteId": "1122334"
    }

For more information, see `Set up Routes for a WebSocket API in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api-add-route.html>`_ in the *Amazon API Gateway Developer Guide*
