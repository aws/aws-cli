**Example 1: To deploy the configured resources for an API to a new Stage**

The following ``create-deployment`` example deploys the configured resources for an API to a new stage. ::

    aws apigateway create-deployment \
        --rest-api-id 1234123412 \
        --stage-name dev \
        --stage-description 'Development Stage' \
        --description 'First deployment to the dev stage'

**Example 2: To deploy the configured resources for an API to an existing stage**

The following ``create-deployment`` example deploys the configured resources for an API to an existing stage. ::

    aws apigateway create-deployment \
        --rest-api-id 1234123412 \
        --stage-name dev \
        --description 'Second deployment to the dev stage'

**Example 3: To deploy the configured resources for an API to an existing stage with Stage Variables**

The following ``create-deployment`` example deploys the configured resources for an API to an existing stage with stage variables. ::

    aws apigateway create-deployment \
        --rest-api-id 1234123412 \
        --stage-name dev \
        --description 'Third deployment to the dev stage' \
        --variables key='value',otherKey='otherValue'

