**To list all the existing versions available in a schema**

The following ``list-schema-versions`` lists all the existing versions available in a schema. ::

	aws schemas list-schema-versions \
		--registry-name example-registry \
		--schema-name example-schema

Output ::

	{
		"SchemaVersions": [
			{
				"SchemaArn": "arn:aws:schemas:us-east-1:012345678912:schema/example-registry/example-schema",
				"SchemaName": "example-schema",
				"SchemaVersion": "2",
				"Type": "OpenApi3"
			},
			{
				"SchemaArn": "arn:aws:schemas:us-east-1:012345678912:schema/example-registry/example-schema",
				"SchemaName": "example-schema",
				"SchemaVersion": "1",
				"Type": "OpenApi3"
			}
		]
	}

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.