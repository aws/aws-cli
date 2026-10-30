**To get the mapping template for a model defined under a REST API**

The following ``get-model-template`` example gets the mapping template for the ``Empty`` model defined under a REST API. ::

    aws apigateway get-model-template \
        --rest-api-id 1234123412 \
        --model-name Empty

Output::

    {
        "value": "#set($inputRoot = $input.path('$'))\n{ }"
    }

For more information, see `Mapping template transformations for REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/models-mappings.html>`__ in the *Amazon API Gateway Developer Guide*.
