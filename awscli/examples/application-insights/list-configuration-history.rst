**To describe the configuration history of a component**

This example uses the ``list-configuration-history`` command to list the INFO, WARN, and ERROR events for periodic configuration updates performed by Application Insights. ::

    aws application-insights list-configuration-history \
        --resource-group-name MYEC2

Output::

    {
        "EventList": [{
            "ResourceGroupName": "MYEC2",
            "AccountId": "123456789012",
            "MonitoredResourceARN": "customizedcomponent-1235a90-b1c2-12c3-be32-12d630f12d55",
            "EventStatus": "INFO",
            "EventResourceType": "CLOUDWATCH_METRIC",
            "EventTime": "2024-05-01T07:00:32.346000+00:00",
            "EventDetail": "Metric Memory Available Mbytes does not exist for component customizedcomponent-1235a90-b1c2-12c3-be32-12d630f12d55, alarm cannot be created. Possible reason might be metric misses data points for two weeks, or required workload to emit this metric not installed.",
            "EventResourceName": "Memory Available Mbytes"
        }, {
            "ResourceGroupName": "MYEC2",
            "AccountId": "123456789012",
            "MonitoredResourceARN": "customizedcomponent-1235a90-b1c2-12c3-be32-12d630f12d55",
            "EventStatus": "INFO",
            "EventResourceType": "CLOUDWATCH_METRIC",
            "EventTime": "2024-05-01T07:00:32.284000+00:00",
            "EventDetail": "Metric Memory % Committed Bytes In Use does not exist for component customizedcomponent-1235a90-b1c2-12c3-be32-12d630f12d55, alarm cannot be created. Possible reason might be metric misses data points for two weeks, or required workload to emit this metric not installed.",
            "EventResourceName": "Memory % Committed Bytes In Use"
        }]
    }