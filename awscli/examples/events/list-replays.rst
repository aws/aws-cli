**To list your replays**

The following ``list-replays`` lists your replays. You can either list all the replays or you can provide a prefix to match to the replay names. Filter parameters are exclusive. ::

	aws events list-replays

Output ::

	{
		"Replays": [
			{
				"ReplayName": "Replay-1",
				"EventSourceArn": "arn:aws:events:us-east-2:123456789012:archive/TestArchive-1",
				"State": "COMPLETED",
				"EventStartTime": "2024-02-21T18:30:00+00:00",
				"EventEndTime": "2024-02-23T09:19:00+00:00",
				"EventLastReplayedTime": "2024-02-23T09:11:00+00:00",
				"ReplayStartTime": "2024-02-23T09:18:51+00:00",
				"ReplayEndTime": "2024-02-23T09:19:53+00:00"
			},
			{
				"ReplayName": "Replay-2",
				"EventSourceArn": "arn:aws:events:us-east-2:123456789012:archive/TestArchive-2",
				"State": "STARTING",
				"EventStartTime": "2024-02-29T18:30:00+00:00",
				"EventEndTime": "2024-03-31T18:29:59+00:00",
				"ReplayStartTime": "2024-04-30T08:43:25+00:00"
			}
		]
	}

For more information, see `Archiving and replaying events in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-archive.html>`__ in the *Amazon EventBridge User Guide*.