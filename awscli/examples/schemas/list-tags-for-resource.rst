**To return the tags present on a registry or schema**

The following ``list-tags-for-resource`` returns the tags present on a registry or schema. ::

	aws schemas list-tags-for-resource \
		--resource-arn arn:aws:schemas:us-east-1:012345678912:registry/example-registry

Output ::

	{
		"Tags": {
			"App": "PetShop",
			"Environment": "Development"
		}
	}

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.