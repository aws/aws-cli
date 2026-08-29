**To describe the status of an existing query**

The following ``get-query-status`` example retrieves a query's current status in an internet monitor. ::

    aws internetmonitor get-query-status \
        --monitor-name TestTCP \
        --query-id AQICAHjE50ADcWtUTXGTlgtIHH4U_u4xxxxxx

Output::

    {
        "Status": "SUCCEEDED"
    }

For more information, see `Use the Internet Monitor query interface <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-IM-view-cw-tools-cwim-query.html>`__ in the *Amazon CloudWatch User Guide*.
