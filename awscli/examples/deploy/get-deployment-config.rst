**To get information about a deployment configuration**

This example displays information about a deployment configuration that is associated with the user's AWS account.

Command::

  aws deploy get-deployment-config --deployment-config-name ThreeQuartersHealthy

Output::

  {
      "deploymentConfigInfo": {
          "deploymentConfigId": "bf6b390b-61d3-4f24-8911-a1664EXAMPLE",
          "minimumHealthyHosts": {
              "type": "FLEET_PERCENT",
              "value": 75
          },
          "createTime": 1411081164.379,
          "deploymentConfigName": "ThreeQuartersHealthy"
      }
  }