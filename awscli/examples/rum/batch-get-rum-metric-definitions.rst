**Retrieves the list of metrics and dimensions that a RUM app monitor is sending to a single destination**

The following ``batch-get-rum-metric-definitions` retrieves the list of metrics and dimensions that a RUM app monitor is sending to a single destination. ::

	aws rum batch-get-rum-metric-definitions \
		--app-monitor-name MyWebApp \
		--destination CloudWatch

Output::

	{
		"MetricDefinitions": [
			{
				"DimensionKeys": {
					"metadata.browserName": "BrowserName",
					"metadata.countryCode": "CountryCode",
					"metadata.deviceType": "DeviceType",
					"metadata.osName": "OSName",
					"metadata.pageId": "PageId"
				},
				"EventPattern": "{\"event_type\":[\"com.amazon.rum.session_start_event\"],\"metadata\":{\"pageId\":[\"/\"],\"browserName\":[\"Firefox\",\"Chrome\",\"Chrome Headless\",\"Edge\",\"IE\",\"Safari\"],\"countryCode\":[\"IN\"],\"deviceType\":[\"mobile\"],\"osName\":[\"Android\",\"iOS\"]}}",
				"MetricDefinitionId": "010c9e15-c0ad-4321-9166-52d8b909b34e",
				"Name": "SessionCount",
				"Namespace": "AWS/RUM",
				"UnitLabel": "Count"
			},
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