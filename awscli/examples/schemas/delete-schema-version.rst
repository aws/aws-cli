**To delete the schema version definition**

The following ``delete-schema-version`` deletes the schema version definition. If the command succeeds, no output is returned. ::

	aws schemas delete-schema-version \
		--registry-name example-registry \
		--schema-name example-schema \
		--schema-version 2

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.