**To flush all authorizer cache entries on a stage**

The following ``flush-stage-authorizers-cache`` example flushes all authorizer cache entries on a stage. ::

    aws apigateway flush-stage-authorizers-cache \
        --rest-api-id 1234123412 \
        --stage-name dev

This command produces no output.

For more information, see `Use API Gateway Lambda authorizers <https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-use-lambda-authorizer.html>`__ in the *Amazon API Gateway Developer Guide*.
