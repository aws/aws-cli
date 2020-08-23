**To retrieve the encrypted secret value of a secret**

The following example shows how to retrieve the secret string value from the version of the secret that has the ``AWSPREVIOUS`` staging label attached. If you want to retrieve the ``AWSCURRENT`` version of the secret, then you can omit the ``--version-stage` parameter because it defaults to ``AWSCURRENT``. ::

	aws secretsmanager get-secret-value --secret-id MyTestDatabaseSecret --version-stage AWSPREVIOUS

The output shows the following: ::

	{
	  "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MyTestDatabaseSecret-a1b2c3",
	  "Name": "MyTestDatabaseSecret",
	  "VersionId": "EXAMPLE1-90ab-cdef-fedc-ba987EXAMPLE",
	  "SecretString": "{\n  \"username\":\"david\",\n  \"password\":\"BnQw&XDWgaEeT9XGTT29\"\n}\n",
	  "VersionStages": [
	    "AWSPREVIOUS"
	  ],
	  "CreatedDate": 1523477145.713
	}
