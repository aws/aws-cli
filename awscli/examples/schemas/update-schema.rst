**To update your existing schema in a registry to a new version**

The following ``update-schema`` will update your existing schema in a registry to a new version. You can specify the type to either OpenApi3 or JSONSchemaDraft4. ::

	aws schemas update-schema \
		--registry-name example-registry \
		--schema-name example-schema \
		--content file://updated-schema.json \
		--type OpenApi3

Contents of ``updated-schema.json``::

	{
	  "openapi": "3.0.0",
	  "info": {
		"version": "1.0.0",
		"title": "Event"
	  },
	  "paths": {},
	  "components": {
		"schemas": {
		  "Event": {
			"type": "object",
			"properties": {
			  "ordinal": {
				"type": "number",
				"format": "int64"
			  },
			  "name": {
				"type": "string"
			  },
			  "description": {
				"type": "string"
			  },
			  "price": {
				"type": "number",
				"format": "double"
			  },
			  "address": {
				"type": "string"
			  },
			  "comments": {
				"type": "array",
				"items": {
				  "type": "string"
				}
			  },
			  "created_at": {
				"type": "string",
				"format": "date-time"
			  }
			}
		  }
		}
	  }
	}

Output ::

	{
		"LastModified": "2024-04-15T17:33:49+00:00",
		"SchemaArn": "arn:aws:schemas:us-east-1:012345678912:schema/example-registry/example-schema",
		"SchemaName": "example-schema",
		"SchemaVersion": "2",
		"Tags": {},
		"Type": "OpenApi3",
		"VersionCreatedDate": "2024-04-15T17:33:49+00:00"
	}

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.