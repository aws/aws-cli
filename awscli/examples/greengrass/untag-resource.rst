**To remove a tag and its value from a resource**

The following ``untag-resource`` example removes the tag whose key is ``Category`` from the specified Greengrass group. If the key ``Category`` does not exist for the specified resource, no error is returned. ::

    aws greengrass untag-resource \
        --resource-arn "arn:aws:greengrass:us-west-2:123456789012:/greengrass/groups/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --tag-keys "Category"
    
This command produces no output.

For more information, see `Tagging your AWS IoT Greengrass resources <https://docs.aws.amazon.com/greengrass/v1/developerguide/tagging.html>`__ in the *AWS IoT Greengrass Version 1 Developer Guide*.
