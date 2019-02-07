**To create an activation**

This example creates a managed instance.

Command::

  aws ssm create-activation --default-instance-name "MyWebServers" --iam-role "AutomationRole" --registration-limit 10

Output::

  {
    "ActivationCode": "Zqr175DJ+sPQRHsmbzzf",
    "ActivationId": "5b9e0074-65d3-4587-8620-3e0b0938db9e"
  }

**To create an activation with an expiration date**

This example creates an Activation code for a managed instance that expires on a specific date.

Command::

  aws ssm create-activation --default-instance-name "MyWebServers" --iam-role "service-role/AmazonEC2RunCommandRoleForManagedInstances" --registration-limit 10 --expiration-date 2019-02-13T19:00:00Z

Output::

{
    "ActivationCode": "i90uMgyDzjCX/EXAMPLE",
    "ActivationId": "cf3cb0a5-c6fb-41fc-96a6-d4096EXAMPLE"
}