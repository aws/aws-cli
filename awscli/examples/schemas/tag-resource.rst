**To add tags to either a schema or registry**

The following ``tag-resource`` adds tags to either a schema or registry. If the command succeeds, no output is returned. ::

	aws schemas tag-resource \
		--resource-arn arn:aws:schemas:region:account:registry/example-registry \
		--tags "{\"Environment\": \"Development\", \"App\": \"PetShop\"}"

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.