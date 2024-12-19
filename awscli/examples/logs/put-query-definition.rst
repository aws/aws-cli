**To Create or update a query definition for CloudWatch Logs Insights**

The following ``put-query-definition`` example creates a query definition for CloudWatch Logs Insights. If the command succeeds, no output is returned. ::

    aws logs put-query-definition \
        --name DemoLogsQueries/Example \
        --log-group-names arn:aws:logs:us-east-1:123456789012:log-group:demo-log-group \
        --query-string "stats sum(packets) as packetsTransferred by srcAddr, dstAddr | sort packetsTransferred desc | limit 100"

Output::

    {
        "queryDefinitionId": "e4ff10e7-144a-4f14-9aef-fbb8f6dd9e6a"
    }

For more information, see `Analyzing log data with CloudWatch Logs Insights <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html>`__ in the *Amazon CloudWatch Logs User Guide*.