**To retrieve the status of a deployment**

The following ``get-deployment-status`` example retrieves the status for the specified deployment of the specified Greengrass group. To get the deployment ID, use the ``list-deployments`` command and specify the group ID. ::

    aws greengrass get-deployment-status \
        --group-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --deployment-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    
Output::

    {
        "DeploymentStatus": "Success",
        "DeploymentType": "NewDeployment",
        "UpdatedAt": "2019-06-18T17:04:44.761Z"
    }

For more information, see `Deploy AWS IoT Greengrass groups to an AWS IoT Greengrass core <https://docs.aws.amazon.com/greengrass/v1/developerguide/deployments.html>`__ in the *AWS IoT Greengrass Developer Guide*.
