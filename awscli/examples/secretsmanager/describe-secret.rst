**To retrieve the details of a secret**

The following example shows how to get the details about a secret. ::

	aws secretsmanager describe-secret --secret-id MyTestDatabaseSecret 

The output shows the following: ::

	{
	  "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MyTestDatabaseSecret-Ca8JGt",
	  "Name": "MyTestDatabaseSecret",
	  "Description": "My test database secret",
	  "LastChangedDate": 1523477145.729,
	  "RotationEnabled": true
	  "RotationLambdaARN": "arn:aws:lambda:us-west-2:123456789012:function:MyTestRotationLambda",
	  "RotationRules": { 
	    "AutomaticallyAfterDays": 30
	  },
	  "LastRotatedDate": 1525747253.72
	  "Tags": [
	    {
	      "Key": "SecondTag",
	      "Value": "AnotherValue"
	    },
	    {
	      "Key": "FirstTag",
	      "Value": "SomeValue"
	    }
	  ],
	  "VersionIdsToStages": {
	    "EXAMPLE1-90ab-cdef-fedc-ba987EXAMPLE": [
	      "AWSPREVIOUS"
	    ],
	    "EXAMPLE2-90ab-cdef-fedc-ba987EXAMPLE": [
	      "AWSCURRENT"
	    ]
	  }
	}