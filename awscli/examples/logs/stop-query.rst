**To Stop a CloudWatch Logs Insights**

The following ``stop-query`` example stops a CloudWatch Logs Insights query that is in progress. ::

    aws logs stop-query \
        --query-id 32b642be-fe54-4b28-a62c-c27fb768a1e2

Output::

    {
        "success": true
    }

For more information, see `Analyzing log data with CloudWatch Logs Insights <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html>`__ in the *Amazon CloudWatch Logs User Guide*.