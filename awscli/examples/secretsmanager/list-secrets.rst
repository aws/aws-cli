**To list the secrets in your account**

The following example shows how to list all of the secrets in your account. ::

	aws secretsmanager list-secrets 

The output shows the following: ::

	{
	  "SecretList": [
	    {
	      "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MyTestDatabaseSecret-a1b2c3",
	      "Name": "MyTestDatabaseSecret",
	      "Description": "My test database secret",
	      "LastChangedDate": 1523477145.729,
	      "SecretVersionsToStages": {
	        "EXAMPLE1-90ab-cdef-fedc-ba987EXAMPLE": [
	          "AWSCURRENT"
	        ]
	      }
	    },
	    {
	      "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MyTestDatabaseSecret1-d4e5f6",
	      "Name": "MyTestDatabaseSecret1",
	      "Description": "Another secret created for a different database",
	      "LastChangedDate": 1523482025.685,
	      "SecretVersionsToStages": {
	        "EXAMPLE2-90ab-cdef-fedc-ba987EXAMPLE": [
	          "AWSCURRENT"
	        ]
	      }
	    }
	  ]
	}