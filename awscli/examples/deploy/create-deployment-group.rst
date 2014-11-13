**To create a deployment group**

This example creates a deployment group and associates it with the specified application and the user's AWS account.

Command::

  aws deploy create-deployment-group --application-name WordPress_App --auto-scaling-groups CodeDeployDemo-ASG --deployment-config-name CodeDeployDefault.OneAtATime --deployment-group-name WordPress_DG --ec2-tag-filters Key=Name,Value=CodeDeployDemo,Type=KEY_AND_VALUE --service-role-arn arn:aws:iam::80398EXAMPLE:role/CodeDeployDemoRole

Output::

  {
      "deploymentGroupId": "cdac3220-0e64-4d63-bb50-e68faEXAMPLE"
  }