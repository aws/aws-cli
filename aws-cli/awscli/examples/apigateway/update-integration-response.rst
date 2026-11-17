**Example 1: To change an integration response header to have a static mapping of '*'**

The following ``update-integration-response`` example changes an integration response header to have a static mapping of '*'. ::

    aws apigateway update-integration-response \
        --rest-api-id 1234123412 \
        --resource-id 3gapai \
        --http-method GET \
        --status-code 200 \
        --patch-operations op='replace',path='/responseParameters/method.response.header.Access-Control-Allow-Origin',value='"'"'*'"'"'

Output::

    {
        "statusCode": "200",
        "responseParameters": {
            "method.response.header.Access-Control-Allow-Origin": "'*'"
        }
    }

**Example 2: To remove an integration response header**

The following ``update-integration-response`` example removes an integration response header. ::

    aws apigateway update-integration-response \
        --rest-api-id 1234123412 \
        --resource-id 3gapai \
        --http-method GET \
        --status-code 200 \
        --patch-operations op='remove',path='/responseParameters/method.response.header.Access-Control-Allow-Origin'

Output::

    {
        "statusCode": "200"
    }

For more information, see `Set up an integration response in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-integration-settings-integration-response.html>`__ in the *Amazon API Gateway Developer Guide*.
