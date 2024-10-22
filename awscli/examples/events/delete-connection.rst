**To delete a connection**

The following ``delete-connection`` deletes a connection. ::

	aws events delete-connection \
		--name ProdConnection
		
Output ::

	{
		"ConnectionArn": "arn:aws:events:us-east-1:123456789012:connection/ProdConnection/53eb3384-f1c8-44b6-ba3a-66fe3cc5fd71",
		"ConnectionState": "DELETING",
		"CreationTime": "2024-04-20T07:21:19+00:00",
		"LastModifiedTime": "2024-04-20T07:55:37+00:00",
		"LastAuthorizedTime": "2024-04-20T07:21:19+00:00"
	}

For more information, see `Deleting connections using the EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-target-connection-delete.html>`__ in the *Amazon EventBridge User Guide*.