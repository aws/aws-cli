**To list all the existing registries**

The following ``list-registries`` lists all the existing registries. You may use the --registry-name-prefix flag to narrow down the results. The command will return all registries by default, but you may narrow the results using the --scope flag to narrow down the results to custom or AWS managed registries. ::

	aws schemas list-registries

Output ::

	{
		"Registries": [
			{
				"RegistryArn": "arn:aws:schemas:us-east-1:012345678912:registry/example-registry-name",
				"RegistryName": "example-registry-name",
				"Tags": {}
			}
		]
	}

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.