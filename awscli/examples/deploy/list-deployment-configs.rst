**To get information about deployment configurations**

This example displays information about all deployment configurations that are associated with the user's AWS account.

Command::

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