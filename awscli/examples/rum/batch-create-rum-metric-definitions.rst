**To specify the extended metrics and custom metrics that you want a CloudWatch RUM app monitor to send to a destination**

The following ``batch-create-rum-metric-definitions`` specifies the extended metrics and custom metrics that you want a CloudWatch RUM app monitor to send to a destination. ::

    aws rum batch-create-rum-metric-definitions \
        --app-monitor-name MyWebApp \
        --destination CloudWatch \
        --metric-definitions 'Namespace=PageVisit,Name=AmazonVisitCount,DimensionKeys={event_details.current_url=URL},EventPattern="{\"metadata\":{\"browserName\":[\"Chrome\"]},\"event_type\":[\"my_custom_event\"],\"event_details\":{\"current_url\":[\"amazonaws.com\"]}}"'

Output::

    {
		"Errors": [],
		"MetricDefinitions": [
        {
            "DimensionKeys": {
                "event_details.current_url": "URL"
            },
            "EventPattern": "{\"metadata\":{\"browserName\":[\"Chrome\"]},\"event_type\":[\"my_custom_event\"],\"event_details\":{\"current_url\":[\"amazonaws.com\"]}}",
            "MetricDefinitionId": "8b67gh3-r678-q987-a576-b9fj7kf234kd",
            "Name": "AmazonVisitCount",
            "Namespace": "PageVisit"
        }
		]
	}

For more information, see `CloudWatch RUM <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-RUM.html>`__ in the *Amazon CloudWatch User Guide*.