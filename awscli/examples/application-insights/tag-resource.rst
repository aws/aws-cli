**To add tags to an application**

This example uses the ``tag-resource`` command to add one or more tags to an application. ::

    aws application-insights tag-resource \
        --resource-arn arn:aws:applicationinsights:eu-west-1:012345678901:application/resource-group/testgroup \
        --tags file://tags.json                                                                                

Contents of ``tags.json``::

    [{
        "Key": "sa",
        "Value": "sample"
    }]

This command returns to the prompt if successful.