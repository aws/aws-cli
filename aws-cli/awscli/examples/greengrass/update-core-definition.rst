**To update a core definition**

The following ``update-core-definition`` example changes the name of the specified core definition. You can update only the ``name`` property of a core definition. ::

    aws greengrass update-core-definition \
        --core-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --name "MyCoreDevices"

This command produces no output.

For more information, see `Configure the AWS IoT Greengrass core <https://docs.aws.amazon.com/greengrass/v1/developerguide/gg-core.html>`__ in the *AWS IoT Greengrass Developer Guide*.
