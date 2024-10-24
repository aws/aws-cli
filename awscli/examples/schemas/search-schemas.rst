**To return the results the schemas in a registry that matched with particular keywords**

The following ``search-schemas`` returns the results the schemas in a registry that matched with particular keywords. You may use multiple keywords followed by spaces. ::

	aws schemas search-schemas \
		--registry-name example-registry \
		--keywords "first second"

Output ::

	{
		"Schemas": [
			{
				"RegistryName": "example-registry",
				"SchemaArn": "arn:aws:schemas:us-east-1:012345678912:schema/example-registry/second-schema",
				"SchemaName": "second-schema",
				"SchemaVersions": [
					{
						"CreatedDate": "2024-04-15T15:07:17+00:00",
						"SchemaVersion": "1",
						"Type": "OpenApi3"
					}
				]
			},
			{
				"RegistryName": "example-registry",
				"SchemaArn": "arn:aws:schemas:us-east-1:012345678912:schema/example-registry/first-schema",
				"SchemaName": "first-schema",
				"SchemaVersions": [
					{
						"CreatedDate": "2024-04-15T15:10:39+00:00",
						"SchemaVersion": "1",
						"Type": "OpenApi3"
					}
				]
			}
		]
	}

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.