**To get information about a deployment configuration**

The following ``get-deployment-config`` example displays information about a deployment configuration that is associated with the user's AWS account. ::

    aws deploy get-deployment-config \
        --deployment-config-name ThreeQuartersHealthy

Output::

    {
        "deploymentConfigInfo": {
            "deploymentConfigId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "minimumHealthyHosts": {
                "type": "FLEET_PERCENT",
                "value": 75
            },
            "createTime": 1411081164.379,
            "deploymentConfigName": "ThreeQuartersHealthy"
        }
    }

For more information, see `View deployment configuration details with CodeDeploy <https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-configurations-view-details.html>`__ in the *AWS CodeDeploy User Guide*.
