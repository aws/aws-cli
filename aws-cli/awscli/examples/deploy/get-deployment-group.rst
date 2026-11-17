**To view information about a deployment group**

The following ``get-deployment-group`` example displays information about a deployment group that is associated with the specified application. ::

    aws deploy get-deployment-group \
        --application-name WordPress_App \
        --deployment-group-name WordPress_DG

Output::

    {
        "deploymentGroupInfo": {
            "applicationName": "WordPress_App",
            "autoScalingGroups": [
                {
                    "name": "CodeDeployDemo-ASG"
                }
            ],
            "deploymentConfigName": "CodeDeployDefault.OneAtATime",
            "ec2TagFilters": [
                {
                    "Type": "KEY_AND_VALUE",
                    "Value": "CodeDeployDemo",
                    "Key": "Name"
                }
            ],
            "deploymentGroupId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "serviceRoleArn": "arn:aws:iam::123456789012:role/CodeDeployDemoRole",
            "deploymentGroupName": "WordPress_DG"
        }
    }

For more information, see `View deployment group details with CodeDeploy <https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-groups-view-details.html>`__ in the *AWS CodeDeploy User Guide*.
