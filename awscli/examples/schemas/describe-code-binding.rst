**To describe a code binding status for a particular language for an existing schema and version**

The following ``describe-code-binding`` describes a code binding status for a particular language for an existing schema and version. You may specify the languages like Java8, TypeScript3, Python36, and Go1. ::

	aws schemas describe-code-binding \
		--registry-name example-registry \
		--schema-name example-schema \
		--schema-version 2 \
		--language Python36

Output::

	{
		"CreationDate": "2024-04-12T13:14:40+00:00",
		"LastModified": "2024-04-12T13:14:40+00:00",
		"SchemaVersion": "2",
		"Status": "CREATE_COMPLETE"
	}

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.