**To change the description of a deployment**

The following ``update-deployment`` example changes the description of a deployment. ::

    aws apigateway update-deployment --rest-api-id 1234123412 --deployment-id ztt4m2 --patch-operations op='replace',path='/description',value='newDescription'

Output::

    {
        "description": "newDescription",
        "id": "ztt4m2",
        "createdDate": 1455218022
    }

