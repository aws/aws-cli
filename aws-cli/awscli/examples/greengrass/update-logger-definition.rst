**To update a logger definition**

The following ``update-logger-definition`` example changes the name of the specified logger definition. You can only update the ``name`` property of a logger definition. ::

    aws greengrass update-logger-definition \
        --logger-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --name "LoggingConfigsForSensors"

This command produces no output.

For more information, see `Monitoring with AWS IoT Greengrass logs <https://docs.aws.amazon.com/greengrass/v1/developerguide/greengrass-logs-overview.html>`__ in the *AWS IoT Greengrass Developer Guide*.
