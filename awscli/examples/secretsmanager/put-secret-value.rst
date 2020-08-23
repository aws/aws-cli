**To store a secret value in a new version of a secret**

The following example shows how to create a new version of the secret. Alternatively, you can use the ``update-secret`` command. ::

	aws secretsmanager put-secret-value --secret-id MyTestDatabaseSecret \
	  --secret-string file://mycreds.json 

The output shows the following: ::

	{
	  "ARN": "arn:aws:secretsmanager:us-west-2:128716708097:secret:MyTestDatabaseSecret-Ca8JGt",
	  "Name": "MyTestDatabaseSecret",
	  "VersionId": "dd47d3af-7095-4da5-a267-11707c060178",
	  "VersionStages": [
	    "AWSCURRENT"
	  ]
	}