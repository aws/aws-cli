**To cancel scheduled rotation for a secret**

The following example shows how to cancel rotation for a secret. The operation sets the ``RotationEnabled`` field to false and cancels all scheduled rotations. To resume scheduled rotations, you must re-enable rotation by calling the ``rotate-secret`` operation. ::

	aws secretsmanager cancel-rotate-secret --secret-id MyTestDatabaseSecret

The output shows the following: ::

	{
	  "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MyTestDatabaseSecret-a1b2c3",
	  "Name": "MyTestDatabaseSecret"
	}

