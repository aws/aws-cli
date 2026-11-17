**To get information about a deployment**

The following ``get-deployment`` example gets information about the specified deployment of a REST API. ::

    aws apigateway get-deployment \
        --rest-api-id 1234123412 \
        --deployment-id ztt4m2

Output::

    {
        "description": "myDeployment",
        "id": "ztt4m2",
        "createdDate": 1455218022
    }

For more information, see `Create a deployment for a REST API in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-deployments.html>`__ in the *Amazon API Gateway Developer Guide*.
