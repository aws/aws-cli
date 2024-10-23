**To retrieve details about a replay**

The following ``describe-replay`` retrieves details about a replay. ::

	aws events describe-replay \
		--replay-name "Replay-1"

Output ::

	{
			"ReplayName": "Replay-1",
			"ReplayArn": "arn:aws:events:us-east-2:123456789012:replay/Replay-1",
			"Description": "ProdReplay",
			"State": "COMPLETED",
			"EventSourceArn": "arn:aws:events:us-east-2:123456789012:archive/TestArchive-1",
			"Destination": {
				"Arn": "arn:aws:events:us-east-2:123456789012:event-bus/custom",
				"FilterArns": [
					"arn:aws:events:us-east-2:123456789012:rule/custom/Test-1"
				]
			},
			"EventStartTime": "2024-02-21T18:30:00+00:00",
			"EventEndTime": "2024-02-23T09:19:00+00:00",
			"EventLastReplayedTime": "2024-02-23T09:11:00+00:00",
			"ReplayStartTime": "2024-02-23T09:18:51+00:00",
			"ReplayEndTime": "2024-02-23T09:19:53+00:00"
	}

For more information, see `Archiving and replaying events in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-archive.html>`__ in the *Amazon EventBridge User Guide*.