**To get the list of API keys associated with a Usage Plan**

The following ``get-usage-plan-keys`` example gets the list of API keys associated with the specified usage plan. ::

    aws apigateway get-usage-plan-keys \
        --usage-plan-id a1b2c3

Output::

    {
        "items": [
            {
                "id": "1NbjQzMReAkeEQPNAW8r3dXsU2rDD7fc7f2Sipnu",
                "type": "API_KEY",
                "name": "MyApiKey"
            }
        ]
    }
