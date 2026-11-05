**Example 1: To create a $default route for a WebSocket or HTTP API**

The following ``create-route`` example creates a ``$default`` route for a WebSocket or HTTP API. ::

    aws apigatewayv2 create-route \
        --api-id aabbccddee \
        --route-key '$default'

Output::

    {
        "ApiKeyRequired": false,
        "AuthorizationType": "NONE",
        "RouteKey": "$default",
        "RouteId": "1122334"
    }

For more information, see `Create routes for WebSocket APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/websocket-api-develop-routes.html>`__ in the *Amazon API Gateway Developer Guide*.

**Example 2: To create a route for an HTTP API**

The following ``create-route`` example creates a route named ``signup`` that accepts POST requests. ::

    aws apigatewayv2 create-route \
        --api-id aabbccddee \
        --route-key 'POST /signup'

Output::

    {
        "ApiKeyRequired": false,
        "AuthorizationType": "NONE",
        "RouteKey": "POST /signup",
        "RouteId": "1122334"
    }

For more information, see `Create routes for HTTP APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-routes.html>`__ in the *Amazon API Gateway Developer Guide*.
