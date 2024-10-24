**To start the discoverer associated with an Event Bus**

The following ``start-discoverer`` starts the discoverer associated with an Event Bus. ::

	aws schemas start-discoverer \
		--discoverer-id events-event-bus-default

Output ::

	{
		"DiscovererId": "example-discoverer-id",
		"State": "STARTED"
	}

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.