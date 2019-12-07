**To create a WebSocket API**

The following ``create-api`` example creates a WebSocket API with the specified name. ::

    aws apigatewayv2 create-api \
        --name "myWebSocketApi" \
        --protocol-type WEBSOCKET \
        --route-selection-expression '$request.body.action' 

Output::

    {
        "ApiKeySelectionExpression": "$request.header.x-api-key",
        "Name": "myWebSocketApi",
        "CreatedDate": "2018-11-15T06:23:51Z",
        "ProtocolType": "WEBSOCKET",
        "RouteSelectionExpression": "'$request.body.action'",
        "ApiId": "aabbccddee"
    }

For more information, see `Create a WebSocket API in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api-create-empty-api.html>`_ in the *Amazon API Gateway Developer Guide*.
