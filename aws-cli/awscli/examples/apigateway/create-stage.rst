**Example 1: To create a stage in an API which will contain an existing deployment**

The following ``create-stage`` example creates a stage named ``dev`` in an API, which contains an existing deployment. ::

    aws apigateway create-stage \
        --rest-api-id 1234123412 \
        --stage-name 'dev' \
        --description 'Development stage' \
        --deployment-id a1b2c3

Output::

    {
        "deploymentId": "a1b2c3",
        "stageName": "dev",
        "description": "Development stage",
        "cacheClusterEnabled": false,
        "cacheClusterStatus": "NOT_AVAILABLE",
        "methodSettings": {},
        "tracingEnabled": false,
        "createdDate": "2022-07-18T10:11:18-07:00",
        "lastUpdatedDate": "2022-07-18T10:11:18-07:00"
    }

**Example 2: To create a stage in an API which will contain an existing deployment and custom Stage Variables**

The following ``create-stage`` example creates a stage named ``dev`` in an API, which contains an existing deployment and custom stage variables. ::

    aws apigateway create-stage \
        --rest-api-id 1234123412 \
        --stage-name 'dev' \
        --description 'Development stage' \
        --deployment-id a1b2c3 \
        --variables key='value',otherKey='otherValue'

Output::

    {
        "deploymentId": "a1b2c3",
        "stageName": "dev",
        "description": "Development stage",
        "cacheClusterEnabled": false,
        "cacheClusterStatus": "NOT_AVAILABLE",
        "methodSettings": {},
        "variables": {
            "key": "value",
            "otherKey": "otherValue"
        },
        "tracingEnabled": false,
        "createdDate": "2022-07-18T10:11:18-07:00",
        "lastUpdatedDate": "2022-07-18T10:11:18-07:00"
    }

For more information, see `Set up a stage for a REST API in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-stages.html>`__ in the *Amazon API Gateway Developer Guide*.
