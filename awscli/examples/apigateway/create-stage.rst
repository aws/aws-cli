**Example 1: To create a stage in an API which will contain an existing deployment**

The following ``create-stage`` example creates a stage named ``dev`` in an API, which contains an existing deployment. ::

    aws apigateway create-stage \
        --rest-api-id 1234123412 \
        --stage-name 'dev' \
        --description 'Development stage' \
        --deployment-id a1b2c3

**Example 2: To create a stage in an API which will contain an existing deployment and custom Stage Variables**

The following ``create-stage`` example creates a stage named ``dev`` in an API, which contains an existing deployment and custom stage variables. ::

    aws apigateway create-stage \
        --rest-api-id 1234123412 \
        --stage-name 'dev' \
        --description 'Development stage' \
        --deployment-id a1b2c3 \
        --variables key='value',otherKey='otherValue'
