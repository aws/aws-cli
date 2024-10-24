**To list all discovers across all Event Buses**

The following ``list-discoverers`` lists all discovers across all Event Buses. ::

	aws schemas list-discoverers 

Output ::

	{
		"Discoverers": [
			{
				"DiscovererArn": "arn:aws:schemas:us-east-1:012345678912:discoverer/example-discoverer-name",
				"DiscovererId": "example-discoverer-name",
				"SourceArn": "arn:aws:events:us-east-1:012345678912:event-bus/example-event-bus-name",
				"State": "STARTED",
				"Cross012345678912": true,
				"Tags": {}
			}
		]
	}

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.