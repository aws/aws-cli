**To create a registry**

The following ``create-registry`` creates a registry. ::

	aws schemas create-registry \
		--registry-name example-registry

Output ::

	{
		"RegistryArn": "arn:aws:schemas:us-east-1:123456789012:registry/example-registry",
		"RegistryName": "example-registry",
		"Tags": {}
	}

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.