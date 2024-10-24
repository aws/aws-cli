**To stop the discoverer associated with an Event Bus**

The following ``stop-discoverer`` stops the discoverer associated with an Event Bus. ::

	aws schemas stop-discoverer \
		--discoverer-id events-event-bus-default

Output ::

	{
		"DiscovererId": "example-discoverer-id",
		"State": "STOPPED"
	}

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.