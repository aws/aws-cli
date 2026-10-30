**Example 1: To get the JSON Swagger template for a stage**

The following ``get-export`` example gets the JSON Swagger template for the ``dev`` stage and saves it to a file. ::

    aws apigateway get-export /path/to/filename.json \
        --rest-api-id a1b2c3d4e5 \
        --stage-name dev \
        --export-type swagger

Output::

    {
        "contentType": "application/octet-stream",
        "contentDisposition": "attachment; filename=\"swagger_2016-02-22_23-52Z.json\""
    }

For more information, see `Export a REST API from API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-export-api.html>`__ in the *Amazon API Gateway Developer Guide*.

**Example 2: To get the JSON Swagger template + API Gateway Extensions for a stage**

The following ``get-export`` example gets the JSON Swagger template with API Gateway Extensions for the ``dev`` stage and saves it to a file. ::

    aws apigateway get-export /path/to/filename.json \
        --parameters extensions='integrations' \
        --rest-api-id a1b2c3d4e5 \
        --stage-name dev \
        --export-type swagger

Output::

    {
        "contentType": "application/octet-stream",
        "contentDisposition": "attachment; filename=\"swagger_2016-02-22_23-52Z.json\""
    }

For more information, see `Export a REST API from API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-export-api.html>`__ in the *Amazon API Gateway Developer Guide*.

**Example 3: To get the JSON Swagger template + Postman Extensions for a stage**

The following ``get-export`` example gets the JSON Swagger template with Postman Extensions for the ``dev`` stage and saves it to a file. ::

    aws apigateway get-export /path/to/filename.json \
        --parameters extensions='postman' \
        --rest-api-id a1b2c3d4e5 \
        --stage-name dev \
        --export-type swagger

Output::

    {
        "contentType": "application/octet-stream",
        "contentDisposition": "attachment; filename=\"swagger_2016-02-22_23-52Z.json\""
    }

For more information, see `Export a REST API from API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-export-api.html>`__ in the *Amazon API Gateway Developer Guide*.
