 **To update an existing endpoint**

The following ``update-endpoint`` will update an existing endpoint. ::

	aws events update-endpoint \
		--name test \
		--description "test endpoint"

Output ::

	{
		"Name": "test",
		"Arn": "arn:aws:events:us-east-1:123456789101:endpoint/test",
		"RoutingConfig": {
			"FailoverConfig": {
				"Primary": {
					"HealthCheck": "arn:aws:route53:::healthcheck/8f7dc0b8-ad9e-1234-846e-3a475c53bb76"
				},
				"Secondary": {
					"Route": "us-east-2"
				}
			}
		},
		"ReplicationConfig": {
			"State": "ENABLED"
		},
		"EventBuses": [
			{
				"EventBusArn": "arn:aws:events:us-east-1:123456789101:event-bus/test"
			},
			{
				"EventBusArn": "arn:aws:events:us-east-2:123456789101:event-bus/test"
			}
		],
		"RoleArn": "arn:aws:iam::123456789101:role/service-role/Amazon_EventBridge_Invoke_Event_Bus_694447205",
		"EndpointId": "3slpsr0pnp.veo",
		"EndpointUrl": "https://3slpsr0pnp.veo.endpoint.events.amazonaws.com",
		"State": "ACTIVE"
	}

For more information, see `Global endpoint in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-ge-create-endpoint.html>`__ in the *Amazon EventBridge User Guide*.