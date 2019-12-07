**To add a label to latest version of a parameter**

This example adds a label to the latest version of a parameter.

Command::

  aws ssm label-parameter-version --name "softwareversion" --labels "DevelopmentReady"
  
Output::

  {
    "InvalidLabels": []
  }

**To add a label to a specific version of a parameter**

This example adds a label to the specified version of a parameter.

Command::

  aws ssm label-parameter-version --name "softwareversion" --parameter-version "2" --labels "ProductionReady"
