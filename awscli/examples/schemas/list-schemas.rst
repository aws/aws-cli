**To list all the existing schemas available in a registry**

The following ``list-schemas`` lists all the existing schemas available in a registry. You may optionally use the --schema-name-prefix to narrow down the results. ::

	aws schemas list-schemas \
		--registry-name example-registry

Output ::

	{
		"Schemas": [
			{
				"LastModified": "2024-04-12T13:56:59+00:00",
				"SchemaArn": "arn:aws:schemas:us-east-1:012345678912:schema/example-registry/example-schema",
				"SchemaName": "example-schema",
				"Tags": {},
				"VersionCount": 2
			}
		]
	}

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.