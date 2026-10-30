**Example 1: To get the JSON Swagger template for a stage**

Command::

    aws apigateway get-export --rest-api-id a1b2c3d4e5 --stage-name dev --export-type swagger /path/to/filename.json

**Example 2: To get the JSON Swagger template + API Gateway Extensions for a stage**

Command::

    aws apigateway get-export --parameters extensions='integrations' --rest-api-id a1b2c3d4e5 --stage-name dev --export-type swagger /path/to/filename.json

**Example 3: To get the JSON Swagger template + Postman Extensions for a stage**

Command::

    aws apigateway get-export --parameters extensions='postman' --rest-api-id a1b2c3d4e5 --stage-name dev --export-type swagger /path/to/filename.json

