**To list all of the secret versions associated with a secret**

The following example shows how to retrieve a list of all of the versions of a secret, including those without any staging labels. ::

	aws secretsmanager list-secret-version-ids --secret-id MyTestDatabaseSecret \
	  --include-deprecated

The output shows the following: ::

	{
	  "Versions": [
	    {
	      "VersionId": "EXAMPLE1-90ab-cdef-fedc-ba987EXAMPLE",
	      "VersionStages": [
	        "AWSPREVIOUS"
	      ],
	      "CreatedDate": 1523477145.713
	    },
	    {
	      "VersionId": "EXAMPLE2-90ab-cdef-fedc-ba987EXAMPLE",
	      "VersionStages": [
	        "AWSCURRENT"
	      ],
	     "CreatedDate": 1523486221.391
	    },
	    {
	      "CreatedDate": 1.51197446236E9,
	      "VersionId": "EXAMPLE3-90ab-cdef-fedc-ba987EXAMPLE;"
	    }
	  ],
	  "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MyTestDatabaseSecret-a1b2c3",
	  "Name": "MyTestDatabaseSecret"
	}