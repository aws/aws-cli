**To retrieve the resource-based policy attached to a secret**

The following example shows how to retrieve the resource-based policy that is attached to a secret.  For more information, see `Resource-based Policies` in the *Secrets Manager User Guide*.
.. _`Resource-based Policies`: http://docs.aws.amazon.com/secretsmanager/latest/userguide/auth-and-access_overview.html#auth-and-access_resource-policies :: 

  aws secretsmanager get-resource-policy --secret-id MyTestDatabaseSecret

The output shows the following. It is shown here word-wrapped and with extra white-space removed for clarity. ::

  {
      "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MyTestDatabaseSecret-a1b2c3",
      "Name": "MyTestDatabaseSecret",
      "ResourcePolicy": "{\n\"Version\":\"2012-10-17\",\n\"Statement\":[{\n\"Effect\":\"Allow\",\n
                         \"Principal\":{\n\"AWS\":\"arn:aws:iam::123456789012:root\"\n},\n\"Action\":
                         \"secretsmanager:GetSecretValue\",\n\"Resource\":\"*\"\n}]\n}"
  }