**To create a new code biding source URI for a particular schema version in the language specified**

The following ``put-code-binding`` creates a new code biding source URI for a particular schema version in the language specified. ::

	aws schemas put-code-binding \
		--registry-name example-registry \
		--schema-name example-schema \
		--schema-version 5 \
		--language Python36

Output ::

	{
		"CreationDate": "2024-04-15T14:53:17+00:00",
		"LastModified": "2024-04-15T14:53:17+00:00",
		"SchemaVersion": "5",
		"Status": "CREATE_IN_PROGRESS"
	}

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.