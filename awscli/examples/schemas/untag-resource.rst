**To remove tags to either a schema or registry**

The following ``untag-resource`` removes tags to either a schema or registry. You may specify the tag keys to remove. If the command succeeds, no output is returned. ::

	aws schemas untag-resource \
		--resource-arn arn:aws:schemas:region:account:registry/example-registry \
		--tag-keys Environment App

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.