**To create a custom deployment configuration**

This example creates a custom deployment configuration and associates it with the user's AWS account.

Command::

  aws deploy create-deployment-config --deployment-config-name ThreeQuartersHealthy --minimum-healthy-hosts type=FLEET_PERCENT,value=75

Output::

  {
      "deploymentConfigId": "bf6b390b-61d3-4f24-8911-a1664EXAMPLE"
  }