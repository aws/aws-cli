**To start the specified replay**

The following ``start-replay`` starts the specified replay. Events are not necessarily replayed in the exact same order that they were added to the archive. A replay processes events to replay based on the time in the event, and replays them using 1 minute intervals. If you specify an EventStartTime and an EventEndTime that covers a 20 minute time range, the events are replayed from the first minute of that 20 minute range first. Then the events from the second minute are replayed. You can use DescribeReplay to determine the progress of a replay. The value returned for EventLastReplayedTime indicates the time within the specified time range associated with the last event replayed. ::

		aws events start-replay \
			--replay-name ProdReplay-1 \
			--event-source-arn "arn:aws:events:us-east-2:123456789012:archive/ProdArchive-1" \
			--event-start-time 2024-02-23T00:40:00Z \
			--event-end-time 2024-02-24T00:40:00Z \
			--destination '{"Arn":"arn:aws:events:us-east-2:123456789012:event-bus/custom"}'
			
Ouput ::
	
	{
		"ReplayArn": "arn:aws:events:us-east-2:123456789012:replay/ProdReplay-1",
		"State": "STARTING",
		"ReplayStartTime": "2024-05-19T08:24:40+00:00"
	}

For more information, see `Archiving and replaying events in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-archive.html>`__ in the *Amazon EventBridge User Guide*.