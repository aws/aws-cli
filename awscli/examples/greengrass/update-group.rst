**To update the group name**

The following ``update-group`` example updates the name of the specified Greengrass group. If you want to update the details for the group, use the ``create-group-version`` command to create a new version. ::

    aws greengrass update-group \
        --group-id "1402daf9-71cf-4cfe-8be0-d5e80526d0d8" \
        --name TestGroup4of6

This command produces no output.

For more information, see `Provision an AWS IoT thing to use as a Greengrass core <https://docs.aws.amazon.com/greengrass/v1/developerguide/provision-core.html>`__ in the *AWS IoT Greengrass Developer Guide*.