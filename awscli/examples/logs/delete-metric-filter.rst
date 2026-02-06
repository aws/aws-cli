**To delete the specified metric filter**

The following ``delete-metric-filter`` example deletes the metric filter named ``demoFilter``. ::

    aws logs delete-metric-filter \
        --log-group-name demo-log-group \
        --filter-name demoMetricFilter

This command produces no output.

For more information, see `Creating metrics from log events using filters <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/MonitoringLogData.html>`__ in the *Amazon CloudWatch Logs User Guide*.