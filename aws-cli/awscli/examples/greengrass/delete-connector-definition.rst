**To delete a connector definition**

The following ``delete-connector-definition`` example deletes the specified Greengrass connector definition. If you delete a connector definition that is used by a group, that group can't be deployed successfully. ::

    aws greengrass delete-connector-definition \
        --connector-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

This command produces no output.

For more information, see `Integrate with services and protocols using Greengrass connectors <https://docs.aws.amazon.com/greengrass/v1/developerguide/connectors.html>`__ in the *AWS IoT Greengrass Developer Guide*.
