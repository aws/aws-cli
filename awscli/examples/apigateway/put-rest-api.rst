**Example 1: To overwrite an existing API using a Swagger template**

The following ``put-rest-api`` example overwrites an existing API using a Swagger template. ::

    aws apigateway put-rest-api --rest-api-id 1234123412 --mode overwrite --body 'fileb:///path/to/API_Swagger_template.json'

**Example 2: To merge a Swagger template into an existing API**

The following ``put-rest-api`` example merges a Swagger template into an existing API. ::

    aws apigateway put-rest-api --rest-api-id 1234123412 --mode merge --body 'fileb:///path/to/API_Swagger_template.json'
