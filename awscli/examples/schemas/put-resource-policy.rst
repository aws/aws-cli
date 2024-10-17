**To create or update the resouce-based policy on the registry**

The following ``put-resource-policy`` creates or updates the resouce-based policy on the registry. ::

	aws schemas put-resource-policy \
		--policy file://resource-based-policy.json \
		--registry-name example-registry

Contents of ``resource-based-policy.json``::

	{
	  "Version": "2012-10-17",
	  "Statement": [{
		"Sid": "AllowReadWrite",
		"Effect": "Allow",
		"Principal": {
		  "AWS": "*"
		},
		"Action": "schemas:*",
		"Resource": ["arn:aws:schemas:us-east-1:012345678912:registry/example-registry", "arn:aws:schemas:us-east-1:012345678912:schema/example-registry*"]
	  }]
	}

Output ::

	{
		"Policy": "{\n  \"Version\": \"2012-10-17\",\n  \"Statement\": [{\n    \"Sid\": \"AllowReadWrite\",\n    \"Effect\": \"Allow\",\n    \"Principal\": {\n      \"AWS\": \"*\"\n    },\n    \"Action\": \"schemas:*\",\n    \"Resource\": [\"arn:aws:schemas:us-east-1:012345678912:registry/example-registry\", \"arn:aws:schemas:us-east-1:012345678912:schema/example-registry*\"]\n  }]\n}\n",
		"RevisionId": "66b7abe2-3af1-493a-a8a6-86f7fb2e5543"
	}

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.