**To restore a previously deleted secret**

The following example shows how to restore a secret that you previously scheduled for deletion. ::

	aws secretsmanager restore-secret --secret-id MyTestDatabaseSecret 

The output shows the following: ::

	{
	  "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MyTestDatabaseSecret-a1b2c3",
	  "Name": "MyTestDatabaseSecret"
	}