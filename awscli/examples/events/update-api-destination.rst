**To update an API destination**

The following ``update-api-destination`` will update an API destination. ::

	aws events update-api-destination \
		--name Prod-api-dest \
		--description "Prod destination"

Output ::

	{
		"ApiDestinationArn": "arn:aws:events:us-east-1:123456789101:api-destination/Prod-api-dest/6d228937-24b5-a11a72a7f9",
		"ApiDestinationState": "ACTIVE",
		"CreationTime": "2022-12-12T13:03:41+05:30",
		"LastModifiedTime": "2024-05-19T15:31:43+05:30"
	}

For more information, see `API destinations as targets in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/laProd/userguide/eb-api-destinations.html>`__ in the *Amazon EventBridge User Guide*.