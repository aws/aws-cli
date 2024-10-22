**To create a global endpoint**

The following ``create-endpoint`` creates a global endpoint. Global endpoints improve your application’s availability by making it regional-fault tolerant. To do this, you define a primary and secondary Region with event buses in each Region. You also create a Amazon Route 53 health check that will tell EventBridge to route events to the secondary Region when an “unhealthy” state is encountered and events will be routed back to the primary Region when the health check reports a “healthy” state. ::

	aws events create-endpoint \
		--name WestProdConnection \
		--event-buses '[{"EventBusArn":"arn:aws:events:us-east-1:123456789012:event-bus/default"},{"EventBusArn":"arn:aws:events:us-east-2:123456789012:event-bus/default"}]' \
		--replication-config '{"State":"ENABLED"}' --routing-config '{"FailoverConfig":{"Primary":{"HealthCheck":"arn:aws:route53:::healthcheck/7f4243fa-ce7e-493b-b3de-4d2058e52ce7"},"Secondary":{"Route":"us-east-2"}}}' \
		--role-arn arn:aws:iam::123456789012:role/service-role/Amazon_EventBridge_Invoke_Event_Bus_468661116
 
Output ::

	{
		"Name": "WestProdConnection",
		"Arn": "arn:aws:events:us-east-1:123456789012:endpoint/WestProdConnection",
		"RoutingConfig": {
			"FailoverConfig": {
				"Primary": {
					"HealthCheck": "arn:aws:route53:::healthcheck/7f4243fa-ce7e-493b-b3de-4d2058e52ce7"
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
				"EventBusArn": "arn:aws:events:us-east-1:123456789012:event-bus/default"
			},
			{
				"EventBusArn": "arn:aws:events:us-east-2:123456789012:event-bus/default"
			}
		],
		"RoleArn": "arn:aws:iam::123456789012:role/service-role/Amazon_EventBridge_Invoke_Event_Bus_468661116",
		"State": "CREATING"
	}

For more information, see `Creating a global endpoint in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-ge-create-endpoint.html>`__ in the *Amazon EventBridge User Guide*.