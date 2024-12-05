**To remove all authorization parameters from the connection**

The following ``deauthorize-connection`` removes all authorization parameters from the connection. This lets you remove the secret from the connection so you can reuse it without having to create a new connection. ::

	aws events deauthorize-connection \
		--name ProdConnection
 
Output ::

	{
		"ConnectionArn": "arn:aws:events:123456789012:connection/ProdConnection/53eb3384-f1c8-44b6-ba3a-66fe3cc5fd71",
		"ConnectionState": "DEAUTHORIZING",
		"CreationTime": "2024-04-20T07:21:19+00:00",
		"LastModifiedTime": "2024-04-20T07:21:19+00:00",
		"LastAuthorizedTime": "2024-04-20T07:21:19+00:00"
	}

For more information, see `De-authorizing connections using the EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-target-connection-deauthorize.html>`__ in the *Amazon EventBridge User Guide*.