**To get a list of deployments for a REST API**

The following ``get-deployments`` example gets a list of deployments for the specified REST API. ::

    aws apigateway get-deployments \
        --rest-api-id 1234123412

Output::

    {
        "items": [
            {
                "createdDate": 1453797217,
                "id": "0a2b4c",
                "description": "Deployed my API for the first time"
            }
        ]
    }

For more information, see `Create a deployment for a REST API in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-deployments.html>`__ in the *Amazon API Gateway Developer Guide*.
