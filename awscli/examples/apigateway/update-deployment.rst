**To change the description of a deployment**

The following ``update-deployment`` example changes the description of a deployment. ::

    aws apigateway update-deployment \
        --rest-api-id 1234123412 \
        --deployment-id ztt4m2 \
        --patch-operations op='replace',path='/description',value='newDescription'

Output::

    {
        "description": "newDescription",
        "id": "ztt4m2",
        "createdDate": 1455218022
    }

For more information, see `Deploy REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-deploy-api.html>`__ in the *Amazon API Gateway Developer Guide*.
