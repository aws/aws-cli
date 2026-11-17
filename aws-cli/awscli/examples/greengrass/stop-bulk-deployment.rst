**To stop a bulk deployment**

The following ``stop-bulk-deployment`` example stops the specified bulk deployment. If you try to stop a bulk deployment that is complete, you receive the ``InvalidInputException: Cannot change state of finished execution.`` error. ::

    aws greengrass stop-bulk-deployment \
        --bulk-deployment-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

This command produces no output.

For more information, see `Create bulk deployments for groups <https://docs.aws.amazon.com/greengrass/v1/developerguide/bulk-deploy-cli.html>`__ in the *AWS IoT Greengrass Developer Guide*.
