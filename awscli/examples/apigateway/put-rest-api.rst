**To overwrite an existing API in the specified region using a Swagger template**

Command::

  aws apigateway put-rest-api --rest-api-id 1234123412 --mode overwrite --body 'file:///path/to/API_Swagger_template.json' --region us-west-2

**To merge a Swagger template into an existing API in the specified region**

Command::

  aws apigateway put-rest-api --rest-api-id 1234123412 --mode merge --body 'file:///path/to/API_Swagger_template.json' --region us-west-2

