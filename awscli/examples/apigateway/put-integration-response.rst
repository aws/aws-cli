**Example 1: To create an integration response as the default response with a mapping template defined**

The following ``put-integration-response`` example creates an integration response as the default response with a mapping template defined. ::

    aws apigateway put-integration-response \
        --rest-api-id 1234123412 \
        --resource-id a1b2c3 \
        --http-method GET \
        --status-code 200 \
        --selection-pattern "" \
        --response-templates '{"application/json": "{\"json\": \"template\"}"}'

Output::

    {
        "statusCode": "200",
        "selectionPattern": "",
        "responseTemplates": {
            "application/json": "{\"json\": \"template\"}"
        }
    }

For more information, see `Set up an integration response in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-integration-settings-integration-response.html>`__ in the *Amazon API Gateway Developer Guide*.

**Example 2: To create an integration response with a regex of 400 and a statically defined header value**

The following ``put-integration-response`` example creates an integration response with a regex of 400 and a statically defined header value. ::

    aws apigateway put-integration-response \
        --rest-api-id 1234123412 \
        --resource-id a1b2c3 \
        --http-method GET \
        --status-code 400 \
        --selection-pattern 400 \
        --response-parameters '{"method.response.header.custom-header": "'"'"'custom-value'"'"'"}'

Output::

    {
        "statusCode": "400",
        "selectionPattern": "400",
        "responseParameters": {
            "method.response.header.custom-header": "'custom-value'"
        }
    }

For more information, see `Set up an integration response in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-integration-settings-integration-response.html>`__ in the *Amazon API Gateway Developer Guide*.
