**To get the mapping template for a model defined under a REST API**

The following ``get-model-template`` example gets the mapping template for the ``Empty`` model defined under a REST API. ::

    aws apigateway get-model-template --rest-api-id 1234123412 --model-name Empty

Output::

    {
        "value": "#set($inputRoot = $input.path('$'))\n{ }"
    }

