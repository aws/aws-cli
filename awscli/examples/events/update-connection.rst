**To update settings for a connection**

The following ``update-connection`` updates settings for a connection. ::

	aws events update-connection \
		--name Prod \
		--description "prod connection"

Output ::

	{
		"ConnectionArn": "arn:aws:events:us-east-1:123456789101:connection/Prod/e9820747-32=88cf9",
		"ConnectionState": "AUTHORIZED",
		"CreationTime": "2022-12-12T13:03:41+05:30",
		"LastModifiedTime": "2024-05-19T15:33:24+05:30",
		"LastAuthorizedTime": "2022-12-12T13:03:41+05:30"
	}

For more information, see `Connections for HTTP endpoint targets in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/laProd/userguide/eb-target-connection.html>`__ in the *Amazon EventBridge User Guide*.