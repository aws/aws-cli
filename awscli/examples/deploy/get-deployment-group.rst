**To view information about a deployment group**

This example displays information about a deployment group that is associated with the specified application.

Command::

  aws deploy get-deployment-group --application-name WordPress_App --deployment-group-name WordPress_DG

Output::

  {
      "deploymentGroupInfo": {
          "applicationName": "WordPress_App",
          "autoScalingGroups": [
		      "CodeDeployDemo-ASG"
	      ],
          "deploymentConfigName": "CodeDeployDefault.OneAtATime",
          "ec2TagFilters": [
              {
                  "Type": "KEY_AND_VALUE",
                  "Value": "CodeDeployDemo",
                  "Key": "Name"
              }
          ],
          "deploymentGroupId": "cdac3220-0e64-4d63-bb50-e68faEXAMPLE",
          "serviceRoleArn": "arn:aws:iam::80398EXAMPLE:role/CodeDeployDemoRole",
          "deploymentGroupName": "WordPress_DG"
      }
  }