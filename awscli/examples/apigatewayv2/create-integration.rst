**To create a WebSocket API Integration Request**

The following ``create-integration`` requests an integration for a WebSocket API. ::

    aws apigatewayv2 create-integration \
        --api-id aabbccddee \
        --passthrough-behavior WHEN_NO_MATCH \
        --timeout-in-millis 29000 \
        --connection-type INTERNET
        --request-templates "{\"application/json\": \"{\"statusCode\":200}\"}"
        --integration-type MOCK

Output::

    {
        "PassthroughBehavior": "WHEN_NO_MATCH",
        "TimeoutInMillis": 29000,
        "ConnectionType": "INTERNET",
        "IntegrationResponseSelectionExpression": "${response.statuscode}",
        "RequestTemplates": {
            "application/json": "{"statusCode":200}"
        },
        "IntegrationId": "0abcdef",
        "IntegrationType": "MOCK"
    }

For more information, see `Set up a WebSocket API Integration Request in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api-integration-requests.html>`_ in the *Amazon API Gateway Developer Guide*.
