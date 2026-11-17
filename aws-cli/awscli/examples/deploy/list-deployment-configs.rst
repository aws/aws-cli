**To get information about deployment configurations**

The following ``list-deployment-configs`` example displays information about all deployment configurations that are associated with the user's AWS account. ::

    aws deploy list-deployment-configs

Output::

    {
        "deploymentConfigsList": [
            "ThreeQuartersHealthy",
            "CodeDeployDefault.AllAtOnce",
            "CodeDeployDefault.HalfAtATime",
            "CodeDeployDefault.OneAtATime"
        ]
    }

For more information, see `View deployment configuration details with CodeDeploy <https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-configurations-view-details.html>`__ in the *AWS CodeDeploy User Guide*.
