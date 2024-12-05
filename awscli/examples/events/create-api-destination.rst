**To create an API destination, which is an HTTP invocation endpoint configured as a target for events**

The following ``create-api-destination`` creates an API destination, which is an HTTP invocation endpoint configured as a target for events. ::

	aws events create-api-destination \
		--name prodApiDestination \
		--connection-arn "arn:aws:events:ca-central-1:123456789012:connection/test/e5dd1690-b729-4724-bbd9-390282925efc" \
		--invocation-endpoint "https://test.com/v1" \
		--http-method "POST"

Output ::

	{
		"ApiDestinationArn": "arn:aws:events:ca-central-1:123456789012:api-destination/prodApiDestination/969681cc-82cc-4353-8e77-b74f9764e629",
		"ApiDestinationState": "ACTIVE",
		"CreationTime": "2024-10-21T15:25:05+00:00",
		"LastModifiedTime": "2024-10-21T15:25:05+00:00"
	}

For more information, see `Create an API destination in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-api-destination-create.html>`__ in the *Amazon EventBridge User Guide*.