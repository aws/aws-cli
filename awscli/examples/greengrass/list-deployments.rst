**To list the deployments for a Greengrass group**

The following ``list-deployments`` example lists the deployments for the specified Greengrass group. You can use the ``list-groups`` command to look up your group ID. ::

    aws greengrass list-deployments \
        --group-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "Deployments": [
            {
                "CreatedAt": "2019-06-18T17:04:32.702Z",
                "DeploymentId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "DeploymentType": "NewDeployment",
                "GroupArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/groups/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
            }
        ]
    }

For more information, see `Deploy AWS IoT Greengrass groups to an AWS IoT Greengrass core <https://docs.aws.amazon.com/greengrass/v1/developerguide/deployments.html>`__ in the *AWS IoT Greengrass Version 1 Developer Guide*.
