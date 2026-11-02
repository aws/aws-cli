**To remove an API key from a Usage Plan**

The following ``delete-usage-plan-key`` example removes an API key from a usage plan. ::

    aws apigateway delete-usage-plan-key \
        --usage-plan-id a1b2c3 \
        --key-id 1NbjQzMReAkeEQPNAW8r3dXsU2rDD7fc7f2Sipnu

This command produces no output.

For more information, see `Set up usage plans for REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-create-usage-plans.html>`__ in the *Amazon API Gateway Developer Guide*.
