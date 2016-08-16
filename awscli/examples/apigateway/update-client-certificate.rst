**To update the description of a client certificate in the specified region**

Command::

  aws apigateway update-client-certificate --client-certificate-id a1b2c3 --patch-operations op='replace',path='/description',value='My new description' --region us-west-2

