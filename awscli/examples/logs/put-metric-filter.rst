**To create or update a metric filter**

The following ``put-metric-filter`` example creates a a metric filter named ``DemoFilter``. ::

    aws logs put-metric-filter \
        --log-group-name demo-log-group \
        --filter-name DemoFilter \
        --filter-pattern ERROR \
        --metric-transformations metricName=DemoMetric,metricNamespace=DemoNamespace,metricValue=1,defaultValue=0,unit=Seconds 

This command produces no output.

For more information, see `Creating metrics from log events using filters <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/MonitoringLogData.html>`__ in the *Amazon CloudWatch Logs User Guide*.