**To get information about an API's stage**

The following ``get-stage`` example gets information about the ``dev`` stage of a REST API. ::

    aws apigateway get-stage \
        --rest-api-id 1234123412 \
        --stage-name dev

Output::

    {
        "stageName": "dev",
        "cacheClusterSize": "0.5",
        "cacheClusterEnabled": false,
        "cacheClusterStatus": "NOT_AVAILABLE",
        "deploymentId": "rbh1fj",
        "lastUpdatedDate": 1466802961,
        "createdDate": 1460682074,
        "methodSettings": {
            "*/*": {
                "cacheTtlInSeconds": 300,
                "loggingLevel": "INFO",
                "dataTraceEnabled": false,
                "metricsEnabled": true,
                "unauthorizedCacheControlHeaderStrategy": "SUCCEED_WITH_RESPONSE_HEADER",
                "throttlingRateLimit": 500.0,
                "cacheDataEncrypted": false,
                "cachingEnabled": false,
                "throttlingBurstLimit": 1000,
                "requireAuthorizationForCacheControl": true
            },
            "~1resource/GET": {
                "cacheTtlInSeconds": 300,
                "loggingLevel": "INFO",
                "dataTraceEnabled": false,
                "metricsEnabled": true,
                "unauthorizedCacheControlHeaderStrategy": "SUCCEED_WITH_RESPONSE_HEADER",
                "throttlingRateLimit": 500.0,
                "cacheDataEncrypted": false,
                "cachingEnabled": false,
                "throttlingBurstLimit": 1000,
                "requireAuthorizationForCacheControl": true
            }
        }
    }

For more information, see `Set up a stage for a REST API in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-stages.html>`__ in the *Amazon API Gateway Developer Guide*.
