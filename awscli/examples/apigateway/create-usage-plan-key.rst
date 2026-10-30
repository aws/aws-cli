**To associate an existing API key with a Usage Plan**

The following ``create-usage-plan-key`` example associates an existing API key with a usage plan. ::

    aws apigateway create-usage-plan-key \
        --usage-plan-id a1b2c3 \
        --key-type "API_KEY" \
        --key-id 4vq3yryqm5

Output::

    {
        "id": "4vq3yryqm5",
        "type": "API_KEY",
        "value": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
        "name": "My API Key"
    }

For more information, see `Set up usage plans for REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-create-usage-plans.html>`__ in the *Amazon API Gateway Developer Guide*.
