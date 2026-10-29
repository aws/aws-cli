**To delete a stage in an API**

The following ``delete-stage`` example deletes a stage in an API. ::

    aws apigateway delete-stage \
        --rest-api-id 1234123412 \
        --stage-name 'dev'

This command produces no output.

For more information, see `Set up a stage for a REST API in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-stages.html>`__ in the *Amazon API Gateway Developer Guide*.
