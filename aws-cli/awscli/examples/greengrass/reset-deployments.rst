**To clean up deployment information for a Greengrass group**

The following ``reset-deployments`` example cleans up deployment information for the specified Greengrass group. When you add the ``--force option``, the deployment information is reset without waiting for the core device to respond. ::

    aws greengrass reset-deployments \
        --group-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --force

Output::

    {
        "DeploymentArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/groups/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/deployments/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "DeploymentId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Reset deployments <https://docs.aws.amazon.com/greengrass/v1/developerguide/reset-deployments-scenario.html>`__ in the *AWS IoT Greengrass Developer Guide*.
