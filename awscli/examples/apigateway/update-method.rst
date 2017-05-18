**To modify a method to require an API Key**

Command::

  aws apigateway update-method --rest-api-id 1234123412 --resource-id a1b2c3 --http-method GET --patch-operations op="replace",path="/apiKeyRequired",value="true"

**To modify a method to require IAM Authorization**

Command::

  aws apigateway update-method --rest-api-id 1234123412 --resource-id a1b2c3 --http-method GET --patch-operations op="replace",path="/authorizationType",value="AWS_IAM"
