**To describe the discoverer for a particular Event Bus**

The following ``describe-discoverer`` describes the discoverer for a particular Event Bus. ::

	aws schemas describe-discoverer \
		--discoverer-id example-discoverer-name

Output::

	{
		"DiscovererArn": "arn:aws:schemas:us-east-1:012345678912:discoverer/examlpe-discoverer-name",
		"DiscovererId": "example-discoverer-name",
		"SourceArn": "arn:aws:events:us-east-1:012345678912:event-bus/example-event-bus",
		"State": "STARTED",
		"Cross012345678912": true,
		"Tags": {}
	}

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.