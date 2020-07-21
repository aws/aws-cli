**To delete the resource-based policy attached to a secret**

The following example shows how to delete the resource-based policy that is attached to a secret. For more information, see `Resource-based Policies` in the *Secrets Manager User Guide*.
.. _`Resource-based Policies`: http://docs.aws.amazon.com/secretsmanager/latest/userguide/auth-and-access_overview.html#auth-and-access_resource-policies::

  aws secretsmanager delete-resource-policy --secret-id MyTestDatabaseSecret

The output shows the following. ::

  {
      "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MyTestDatabaseMasterSecret-a1b2c3",
      "Name": "MyTestDatabaseSecret"
  }