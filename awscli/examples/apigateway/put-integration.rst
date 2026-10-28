**Example 1: To create a MOCK integration request**

The following ``put-integration`` example creates a MOCK integration request. ::

    aws apigateway put-integration \
        --rest-api-id 1234123412 \
        --resource-id a1b2c3 \
        --http-method GET \
        --type MOCK \
        --request-templates '{ "application/json": "{\"statusCode\": 200}" }'

**Example 2: To create a HTTP integration request**

The following ``put-integration`` example creates an HTTP integration request. ::

    aws apigateway put-integration \
        --rest-api-id 1234123412 \
        --resource-id a1b2c3 \
        --http-method GET \
        --type HTTP \
        --integration-http-method GET \
        --uri 'https://domain.tld/path'

**Example 3: To create an AWS integration request with a Lambda Function endpoint**

The following ``put-integration`` example creates an AWS integration request with a Lambda function endpoint. ::

    aws apigateway put-integration \
        --rest-api-id 1234123412 \
        --resource-id a1b2c3 \
        --http-method GET \
        --type AWS \
        --integration-http-method POST \
        --uri 'arn:aws:apigateway:us-west-2:lambda:path/2015-03-31/functions/arn:aws:lambda:us-west-2:123412341234:function:function_name/invocations'
