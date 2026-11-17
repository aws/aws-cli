**To retrieve information about a resource definition**

The following ``get-resource-definition`` example retrieves information about the specified resource definition. To retrieve the IDs of your resource definitions, use the ``list-resource-definitions`` command. ::

    aws greengrass get-resource-definition \
        --resource-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/resources/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "CreationTimestamp": "2019-06-19T16:40:59.261Z",
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "LastUpdatedTimestamp": "2019-06-19T16:40:59.261Z",
        "LatestVersion": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/resources/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "tags": {}
    }

For more information, see `Access local resources with Lambda functions and connectors <https://docs.aws.amazon.com/greengrass/v1/developerguide/access-local-resources.html>`__ in the *AWS IoT Greengrass Developer Guide*.
