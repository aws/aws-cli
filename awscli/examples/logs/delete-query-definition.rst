**To Delete a CloudWatch Logs Insights query definition**

The following ``delete-query-definition`` example deletes a saved CloudWatch Logs Insights query definition. ::

    aws logs delete-query-definition \
        --query-definition-id a1b2c3d4-5678-90ab-cdef-example11111

Output::

    {
        "success": true
    }

For more information, see `Analyzing log data with CloudWatch Logs Insights <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html>`__ in the *Amazon CloudWatch Logs User Guide*.