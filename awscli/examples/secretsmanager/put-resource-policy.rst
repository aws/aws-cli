**To add a resource-based policy to a secret**

The following example shows how to add a resource-based policy to a secret. The policy is read from a file on disk and must contain a valid JSON policy document. For more information, see `Resource-based Policies` in the *Secrets Manager User Guide*.
.. _`Resource-based Policies`: http://docs.aws.amazon.com/secretsmanager/latest/userguide/auth-and-access_overview.html#auth-and-access_resource-policies::

  aws secretsmanager put-resource-policy --secret-id MyTestDatabaseMasterSecret \
      --resource-policy file://mysecretpolicy.json 

The output shows the following: ::

  {
      "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MyTestDatabaseSecret-a1b2c3",
      "Name": "MyTestDatabaseSecret"
  }
