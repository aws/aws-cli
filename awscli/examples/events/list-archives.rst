**To list your archives**

The following ``list-archives`` lists your archives. You can either list all the archives or you can provide a prefix to match to the archive names. Filter parameters are exclusive. ::

	aws events list-archives

Output ::

	{
		"Archives": [
			{
				"ArchiveName": "ProdArchive-1",
				"EventSourceArn": "arn:aws:events:us-east-2:123456789101:event-bus/default",
				"State": "ENABLED",
				"RetentionDays": 0,
				"SizeBytes": 235439890,
				"EventCount": 115044,
				"CreationTime": "2023-05-16T04:00:52+00:00"
			},
			{
				"ArchiveName": "ProdArchive-2",
				"EventSourceArn": "arn:aws:events:us-east-2:123456789101:event-bus/custom",
				"State": "ENABLED",
				"RetentionDays": 1,
				"SizeBytes": 0,
				"EventCount": 0,
				"CreationTime": "2023-04-03T03:38:02+00:00"
			}
		]
	}

For more information, see `Archiving and replaying events in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/laProd/userguide/eb-archive.html>`__ in the *Amazon EventBridge User Guide*.