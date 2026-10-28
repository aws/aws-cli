**To get the integration response configuration for a HTTP method defined under a REST API's resource**

The following ``get-integration-response`` example gets the integration response configuration for the ``200`` status code of the ``GET`` method defined under a REST API's resource. ::

    aws apigateway get-integration-response \
        --rest-api-id 1234123412 \
        --resource-id y9h6rt \
        --http-method GET \
        --status-code 200

Output::

    {
        "statusCode": "200",
        "responseTemplates": {
            "application/json": null
        }
    }

