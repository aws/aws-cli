**To change the name of an API in the specified region**

Command::

  aws apigateway update-rest-api --rest-api-id 1234123412 --patch-operations op=replace,path=/name,value='New Name' --region us-west-2

**To change the description of an API in the specified region**

Command::

  aws apigateway update-rest-api --rest-api-id 1234123412 --patch-operations op=replace,path=/description,value='New Description'

