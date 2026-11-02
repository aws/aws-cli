**To update the name for a connector definition**

The following ``update-connector-definition`` example updates the name for the specified connector definition. If you want to update the details for the connector, use the ``create-connector-definition-version`` command to create a new version. ::

    aws greengrass update-connector-definition \
        --connector-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --name "GreengrassConnectors2019"

This command produces no output.

For more information, see `Integrate with services and protocols using Greengrass connectors <https://docs.aws.amazon.com/greengrass/v1/developerguide/connectors.html>`__ in the *AWS IoT Greengrass Developer Guide*.
