**Example 1: To deploy the configured resources for an API to a new Stage**

The following ``create-deployment`` example deploys the configured resources for an API to a new stage. ::

    aws apigateway create-deployment \
        --rest-api-id 1234123412 \
        --stage-name dev \
        --stage-description 'Development Stage' \
        --description 'First deployment to the dev stage'

Output::

    {
        "id": "ztt4m2",
        "description": "First deployment to the dev stage",
        "createdDate": "2022-07-18T10:11:18-07:00"
    }

**Example 2: To deploy the configured resources for an API to an existing stage**

The following ``create-deployment`` example deploys the configured resources for an API to an existing stage. ::

    aws apigateway create-deployment \
        --rest-api-id 1234123412 \
        --stage-name dev \
        --description 'Second deployment to the dev stage'

Output::

    {
        "id": "u3v4x5",
        "description": "Second deployment to the dev stage",
        "createdDate": "2022-07-18T10:19:04-07:00"
    }

**Example 3: To deploy the configured resources for an API to an existing stage with Stage Variables**

The following ``create-deployment`` example deploys the configured resources for an API to an existing stage with stage variables. ::

    aws apigateway create-deployment \
        --rest-api-id 1234123412 \
        --stage-name dev \
        --description 'Third deployment to the dev stage' \
        --variables key='value',otherKey='otherValue'

Output::

    {
        "id": "w5x6y7",
        "description": "Third deployment to the dev stage",
        "createdDate": "2022-07-18T10:25:42-07:00"
    }

For more information, see `Deploy REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-deploy-api.html>`__ in the *Amazon API Gateway Developer Guide*.
