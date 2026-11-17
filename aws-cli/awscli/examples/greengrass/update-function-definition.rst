**To update the name for a function definition**

The following ``update-function-definition`` example updates the name for the specified function definition. If you want to update the details for the function, use the ``create-function-definition-version`` command to create a new version. ::

    aws greengrass update-function-definition \
        --function-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --name ObsoleteFunction

This command produces no output.

For more information, see `Run Lambda functions on the AWS IoT Greengrass core <https://docs.aws.amazon.com/greengrass/v1/developerguide/lambda-functions.html>`__ in the *AWS IoT Greengrass Developer Guide*.
