**To list the versions of a resource definition**

The following ``list-resource-definition-versions`` example lists the versions for the specified Greengrass resource. ::

    aws greengrass list-resource-definition-versions \
        --resource-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    
Output::

    {
        "Versions": [
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/resources/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "CreationTimestamp": "2019-06-19T16:40:59.392Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            },
            {
                "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/resources/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "CreationTimestamp": "2019-06-19T16:40:59.261Z",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
            }
        ]
    }

For more information, see `Access local resources with Lambda functions and connectors <https://docs.aws.amazon.com/greengrass/v1/developerguide/access-local-resources.html>`__ in the *AWS IoT Greengrass Version 1 Developer Guide*.
