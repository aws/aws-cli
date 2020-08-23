**To delete a secret**

The following example shows how to delete a secret. The secret stays in your account in a deprecated and inaccessible state until the recovery window ends. After the date and time in the ``DeletionDate`` response field has passed, you can no longer recover this secret with restore-secret. ::

	aws secretsmanager delete-secret --secret-id MyTestDatabaseSecret1 \
	    --recovery-window-in-days 7 

The output shows the following: ::

	{
	  "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MyTestDatabaseSecret-a1b2c3",
	  "Name": "MyTestDatabaseSecret",
	  "DeletionDate": 1524085349.095
	}