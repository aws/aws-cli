**To delete a connector definition**

The following ``delete-connector-definition`` example deletes the specified Greengrass connector definition. If you delete a connector definition that is used by a group, that group can't be deployed successfully. ::

    aws greengrass delete-connector-definition \
        --connector-definition-id "b5c4ebfd-f672-49a3-83cd-31c7216a7bb8"

This command produces no output.

For more information, see `Integrate with services and protocols using Greengrass connectors <https://docs.aws.amazon.com/greengrass/v1/developerguide/connectors.html>`__ in the *AWS IoT Greengrass Developer Guide*.
