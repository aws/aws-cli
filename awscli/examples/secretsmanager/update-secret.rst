The following examples show how to modify individual components of the secret. Alternatively, you can combine all of the parameters into a single command to do them all in one operation.

**To update the description of a secret**

The following example shows how to modify the description of a secret. ::

	aws secretsmanager update-secret --secret-id MyTestDatabaseSecret \
	  --description "This is a new description for the secret."

The output shows the following: ::

	{
	  "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MyTestDatabaseSecret-a1b2c3",
	  "Name": "MyTestDatabaseSecret"
	}

**To update the KMS key associated with a secret**
	
This example shows how to update the KMS customer managed key (CMK) used to encrypt the secret value. The KMS CMK must be in the same region as the secret. ::

	aws secretsmanager update-secret --secret-id MyTestDatabaseSecret \
	  --kms-key-id arn:aws:kms:us-west-2:123456789012:key/EXAMPLE1-90ab-cdef-fedc-ba987EXAMPLE

The output shows the following: ::

	{
	  "ARN": "arn:aws:secretsmanager:us-west-2:123456789012:secret:MyTestDatabaseSecret-a1b2c3",
	  "Name": "MyTestDatabaseSecret"
	}

**To create a new version of the encrypted secret value**

The following example shows how to create a new version of the secret by updating the --secret-string field. The secret string is read from the contents of the specified file. Alternatively, you can use the put-secret-value operation. ::

	aws secretsmanager update-secret --secret-id MyTestDatabaseSecret \
	  --secret-string file://mycreds.json

The output shows the following, including the ``VersionId`` of the new secret version: ::

	{
	  "ARN": "aws:arn:secretsmanager:us-west-2:123456789012:secret:MyTestDatabaseSecret-a1b2c3",
	  "Name": "MyTestDatabaseSecret",
	  "VersionId": "EXAMPLE1-90ab-cdef-fedc-ba987EXAMPLE"
	}	