**To update an existing discoverer on the Event Bus**

The following ``update-discoverer`` updates an existing discoverer on the Event Bus. You can change the description, or you can enable or disable discovering schemas on cross-012345678912 Events. ::

	aws schemas update-discoverer \
		--discoverer-id example-discoverer-id \
		--no-cross-012345678912

Output ::

	{
		"DiscovererArn": "arn:aws:schemas:us-east-1:012345678912:discoverer/example-discoverer-id",
		"DiscovererId": "example-discoverer-id",
		"SourceArn": "arn:aws:events:us-east-1:012345678912:event-bus/example-event-bus",
		"State": "STOPPED",
		"Cross012345678912": false,
		"Tags": {}
	}

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.