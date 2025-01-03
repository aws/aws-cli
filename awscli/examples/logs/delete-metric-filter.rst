**To Delete the specified metric filter**

The following ``delete-metric-filter`` example deletes the metric filter named ``demoFilter``. If the command succeeds, no output is returned. ::

    aws logs delete-metric-filter \
        --log-group-name demo-log-group \
        --filter-name demoMetricFilter

For more information, see `Creating metrics from log events using filters <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/MonitoringLogData.html>`__ in the *Amazon CloudWatch Logs User Guide*.