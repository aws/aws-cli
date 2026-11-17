**To get the integration configuration for a HTTP method defined under a REST API's resource**

The following ``get-integration`` example gets the integration configuration for the ``GET`` method defined under a REST API's resource. ::

    aws apigateway get-integration \
        --rest-api-id 1234123412 \
        --resource-id y9h6rt \
        --http-method GET

Output::

    {
        "httpMethod": "POST",
        "integrationResponses": {
            "200": {
                "responseTemplates": {
                    "application/json": null
                },
                "statusCode": "200"
            }
        },
        "cacheKeyParameters": [],
        "type": "AWS",
        "uri": "arn:aws:apigateway:us-west-2:lambda:path/2015-03-31/functions/arn:aws:lambda:us-west-2:123456789012:function:My_Function/invocations",
        "cacheNamespace": "y9h6rt"
    }

For more information, see `Integrations for REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-integration-settings.html>`__ in the *Amazon API Gateway Developer Guide*.
