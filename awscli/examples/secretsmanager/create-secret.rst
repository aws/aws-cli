**To create a basic secret**

The following example shows how to create a secret. The credentials stored in the encrypted secret value are retrieved from a file on disk named ``mycreds.json``. ::

	aws secretsmanager create-secret --name MyTestDatabaseSecret \
	    --description "My test database secret created with the CLI" \
	    --secret-string file://mycreds.json 

The output shows the following: ::

	{
	  "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MyTestDatabaseSecret-a1b2c3",
	  "Name": "MyTestDatabaseSecret",
	  "VersionId": "EXAMPLE1-90ab-cdef-fedc-ba987EXAMPLE"
	}