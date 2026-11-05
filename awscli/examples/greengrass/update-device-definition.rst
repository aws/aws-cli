**To update a device definition**

The following ``update-device-definition`` example changes the name of the specified device definition. You can only update the ``name`` property of a device definition. ::

    aws greengrass update-device-definition \
        --device-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --name "TemperatureSensors"

This command produces no output.

For more information, see `Overview of the AWS IoT Greengrass group object model <https://docs.aws.amazon.com/greengrass/v1/developerguide/deployments.html#api-overview>`__ in the *AWS IoT Greengrass Version 1 Developer Guide*.
