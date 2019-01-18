**To add a staging label attached to a version of a secret**

The following example shows you how to add a staging label to a version of a secret. You can review the results by running the command list-secret-version-ids and viewing the VersionStages response field for the affected version. ::

	aws secretsmanager update-secret-version-stage --secret-id MyTestDatabaseSecret \
	  --version-stage STAGINGLABEL1 \
	  --move-to-version-id EXAMPLE1-90ab-cdef-fedc-ba987EXAMPLE

The output shows the following: ::

	{
	  "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MyTestDatabaseSecret-a1b2c3",
	  "Name": "MyTestDatabaseSecret"
	}

**To delete a staging label attached to a version of a secret**

The following example shows you how to delete a staging label that is attached to a version of a secret. You can review the results by running the command list-secret-version-ids and viewing the VersionStages response field for the affected version. ::

	aws secretsmanager update-secret-version-stage --secret-id MyTestDatabaseSecret \
	  --version-stage STAGINGLABEL1 \
	  --remove-from-version-id EXAMPLE1-90ab-cdef-fedc-ba987EXAMPLE

The output shows the following: ::

	{
	  "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MyTestDatabaseSecret-a1b2c3",
	  "Name": "MyTestDatabaseSecret"
	}
	
**To move a staging label from one version of a secret to another**

The following example shows you how to move a staging label that is attached to one version of a secret to a different version. You can review the results by running the command list-secret-version-ids and viewing the VersionStages response field for the affected version. ::

	aws secretsmanager update-secret-version-stage --secret-id MyTestDatabaseSecret \
	  --version-stage AWSCURRENT \
	  --move-to-version-id EXAMPLE1-90ab-cdef-fedc-ba987EXAMPLE \
	  --remove-from-version-id EXAMPLE2-90ab-cdef-fedc-ba987EXAMPLE

The output shows the following: ::

	{
	  "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MyTestDatabaseSecret-a1b2c3",
	  "Name": "MyTestDatabaseSecret"
	}	