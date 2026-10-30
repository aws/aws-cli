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
