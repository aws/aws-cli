**To update the description of a client certificate**

The following ``update-client-certificate`` example updates the description of a client certificate. ::

    aws apigateway update-client-certificate --client-certificate-id a1b2c3 --patch-operations op='replace',path='/description',value='My new description'
