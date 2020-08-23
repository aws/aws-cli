**To configure rotation for a secret**

The following example configures rotation for a secret by providing the ARN of a Lambda rotation function (which must already exist) and the number of days between rotation. The first rotation happens immediately upon completion of this command. The rotation function runs asynchronously in the background. ::

	aws secretsmanager rotate-secret --secret-id MyTestDatabaseSecret \
	  --rotation-lambda-arn arn:aws:lambda:us-west-2:1234566789012:function:MyTestRotationLambda \
	  --rotation-rules AutomaticallyAfterDays=30

The output shows the following, including the ``VersionId`` of the new secret version: ::

	{
	  "ARN": "aws:arn:secretsmanager:us-west-2:123456789012:secret:MyTestDatabaseSecret-a1b2c3",
	  "Name": "MyTestDatabaseSecret",
	  "VersionId": "EXAMPLE1-90ab-cdef-fedc-ba987EXAMPLE"
	}
	
**To request an immediate rotation for a secret**

The following example requests an immediate invocation of the secret's Lambda rotation function. It assumes that the specified secret already has rotation configured. The rotation function runs asynchronously in the background. ::

	aws secretsmanager rotate-secret --secret-id MyTestDatabaseSecret

The output shows the following, including the ``VersionId`` of the new secret version: ::

	{
	  "ARN": "aws:arn:secretsmanager:us-west-2:123456789012:secret:MyTestDatabaseSecret-a1b2c3",
	  "Name": "MyTestDatabaseSecret",
	  "VersionId": "EXAMPLE2-90ab-cdef-fedc-ba987EXAMPLE"
	}	