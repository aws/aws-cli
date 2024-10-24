**To create a discoverer**

The following ``create-discoverer`` creates a discoverer. ::

	aws schemas create-discoverer \
		--source-arn arn:aws:events:us-east-1:123456789012:event-bus/example-event-bus \
		--cross-account

Output ::

	{
		"DiscovererArn": "arn:aws:schemas:us-east-1:123456789012:discoverer/example-discoverer-name",
		"DiscovererId": "example-discoverer-name",
		"SourceArn": "arn:aws:events:us-east-1:123456789012:event-bus/example-event-bus",
		"State": "STARTED",
		"Cross123456789012": true,
		"Tags": {}
	}

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.