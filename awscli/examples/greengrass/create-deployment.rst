**To create a deployment for a version of a Greengrass group**

The following ``create-deployment`` example deploys the specified version of a Greengrass group. ::

    aws greengrass create-deployment \
        --deployment-type NewDeployment \
        --group-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --group-version-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"

Output::

    {
        "DeploymentArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/groups/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/deployments/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
        "DeploymentId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
    }

For more information, see `Getting started with Greengrass connectors (CLI) <https://docs.aws.amazon.com/greengrass/v1/developerguide/connectors-cli.html>`__ in the *AWS IoT Greengrass Developer Guide*.
