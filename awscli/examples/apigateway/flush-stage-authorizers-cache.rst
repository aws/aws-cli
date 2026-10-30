**To flush all authorizer cache entries on a stage**

The following ``flush-stage-authorizers-cache`` example flushes all authorizer cache entries on a stage. ::

    aws apigateway flush-stage-authorizers-cache \
        --rest-api-id 1234123412 \
        --stage-name dev
