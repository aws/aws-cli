**To List the specified metric filters**

The following ``describe-metric-filters`` example lists all metric filters. ::

    aws logs describe-metric-filters

Output::

    {
        "metricFilters": [
            {
                "filterName": "DemoFilter",
                "filterPattern": "ERROR",
                "metricTransformations": [
                    {
                        "metricName": "Demo_Error",
                        "metricNamespace": "DemoNamespace",
                        "metricValue": "1"
                    }
                ],
                "creationTime": 1713432753126,
                "logGroupName": "demo-log-group"
            }
        ]
    }

For more information, see `Creating metrics from log events using filters <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/MonitoringLogData.html>`__ in the *Amazon CloudWatch Logs User Guide*.