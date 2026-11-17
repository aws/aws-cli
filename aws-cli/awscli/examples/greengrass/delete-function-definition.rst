**To delete a function definition**

The following ``delete-function-definition`` example deletes the specified Greengrass function definition. If you delete a function definition that is used by a group, that group can't be deployed successfully. ::

    aws greengrass delete-function-definition \
        --function-definition-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

This command produces no output.

For more information, see `Run Lambda functions on the AWS IoT Greengrass core <https://docs.aws.amazon.com/greengrass/v1/developerguide/lambda-functions.html>`__ in the *AWS IoT Greengrass Developer Guide*.
