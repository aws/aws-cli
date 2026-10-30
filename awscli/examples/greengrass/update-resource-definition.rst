**To update the name for a resource definition**

The following ``update-resource-definition`` example updates the name for the specified resource definition. If you want to change the details for the resource, use the ``create-resource-definition-version`` command to create a new version. ::

    aws greengrass update-resource-definition \
        --resource-definition-id "c8bb9ebc-c3fd-40a4-9c6a-568d75569d38" \
        --name GreengrassConnectorResources

This command produces no output.

For more information, see `Access local resources with Lambda functions and connectors <https://docs.aws.amazon.com/greengrass/v1/developerguide/access-local-resources.html>`__ in the *AWS IoT Greengrass Developer Guide*.
