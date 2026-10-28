**To import a Swagger template and create an API**

The following ``import-rest-api`` example imports a Swagger template and creates an API. ::

    aws apigateway import-rest-api \
        --body 'fileb:///path/to/API_Swagger_template.json'
