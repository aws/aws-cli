**To list the tags attached to a resource**

The following ``list-tags-for-resource`` example lists the tags and their values that are attached to the specified resource. ::

    aws greengrass list-tags-for-resource \
        --resource-arn "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/resources/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    
Output::

    {
        "tags": {
            "ResourceSubType": "USB",
            "ResourceType": "Device"
        }
    }

For more information, see `Tagging your AWS IoT Greengrass resources <https://docs.aws.amazon.com/greengrass/v1/developerguide/tagging.html>`__ in the *AWS IoT Greengrass Version 1 Developer Guide*.
