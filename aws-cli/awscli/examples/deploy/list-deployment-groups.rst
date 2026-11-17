**To get information about deployment groups**

The following ``list-deployment-groups`` example displays information about all deployment groups that are associated with the specified application. ::

    aws deploy list-deployment-groups \
        --application-name WordPress_App

Output::

    {
        "applicationName": "WordPress_App",
        "deploymentGroups": [
            "WordPress_DG",
            "WordPress_Beta_DG"
        ]
    }

For more information, see `View deployment group details with CodeDeploy <https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-groups-view-details.html>`__ in the *AWS CodeDeploy User Guide*.
