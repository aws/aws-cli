**To get the details of an API key associated with a Usage Plan**

The following ``get-usage-plan-key`` example gets the details of an API key associated with the specified usage plan. ::

    aws apigateway get-usage-plan-key \
        --usage-plan-id a1b2c3 \
        --key-id 1NbjQzMReAkeEQPNAW8r3dXsU2rDD7fc7f2Sipnu

Output::

    {
        "id": "1NbjQzMReAkeEQPNAW8r3dXsU2rDD7fc7f2Sipnu",
        "type": "API_KEY",
        "name": "MyApiKey"
    }

For more information, see `Set up usage plans for REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-create-usage-plans.html>`__ in the *Amazon API Gateway Developer Guide*.
