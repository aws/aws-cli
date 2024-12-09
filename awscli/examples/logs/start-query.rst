**To Schedule a query of a log group using CloudWatch Logs Insights**

The following ``start-query`` example performs CloudWatch Logs Insights query on the log group ``demo-log-group`` to find 25 most recently added log events. ::

    aws logs start-query \
        --log-group-name demo-log-group \
        --start-time 1712829536000 \
        --end-time 1712833136000 \
        --query-string "fields @timestamp, @message | sort @timestamp desc" \
        --limit 25

Output::

    {
        "queryId": "2dac81d5-a6a5-45d7-b355-c842b1a7c0c5"
    }

For more information, see `Analyzing log data with CloudWatch Logs Insights <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html>`__ in the *Amazon CloudWatch Logs User Guide*.