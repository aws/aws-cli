**To apply tags to a resource**

The following ``tag-resource`` example applies two tags, ``ResourceType`` and ``ResourceSubType``, to the specified Greengrass resource. This operation can both add new tags and values or update the value for existing tags.  Use the ``untag-resource`` command to remove a tag. ::

    aws greengrass tag-resource \
        --resource-arn "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/resources/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --tags "ResourceType=Device,ResourceSubType=USB"
    
This command produces no output.

For more information, see `Tagging your AWS IoT Greengrass resources <https://docs.aws.amazon.com/greengrass/v1/developerguide/tagging.html>`__ in the *AWS IoT Greengrass Version 1 Developer Guide*.
