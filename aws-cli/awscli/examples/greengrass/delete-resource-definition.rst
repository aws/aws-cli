**To delete a resource definition**

The following ``delete-resource-definition`` example deletes the specified resource definition, including all resource versions. If you delete a resource definition that is used by a group, that group can't be deployed successfully. ::

    aws greengrass delete-resource-definition \
        --resource-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

This command produces no output.

For more information, see `Access local resources with Lambda functions and connectors <https://docs.aws.amazon.com/greengrass/v1/developerguide/access-local-resources.html>`__ in the *AWS IoT Greengrass Developer Guide*.
