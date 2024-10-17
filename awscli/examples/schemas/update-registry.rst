**To update an existing registry**

The following ``update-registry`` will update an existing registry. You may update the registry’s description. ::

	aws schemas update-registry \
		--registry-name example-registry \
		--description "Registry for development environment"

Output ::

	{
		"Description": "Registry for development environment",
		"RegistryArn": "arn:aws:schemas:us-east-1:012345678912:registry/example-registry",
		"RegistryName": "example-registry",
		"Tags": {}
	}

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.