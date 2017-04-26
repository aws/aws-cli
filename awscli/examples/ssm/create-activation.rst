**To create an activation**

This example creates a managed instance.

Command::

  aws ssm create-activation --default-instance-name "MyWebServers" --iam-role "AutomationRole" --registration-limit 10

Output::

  {
    "ActivationCode": "Zqr175DJ+sPQRHsmbzzf",
    "ActivationId": "5b9e0074-65d3-4587-8620-3e0b0938db9e"
  }
