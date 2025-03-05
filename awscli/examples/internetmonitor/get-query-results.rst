**To fetch the results of a query**

The following ``get-query-results`` example retrieves the results of a query performed in a monitor. ::

    aws internetmonitor get-query-results \
        --monitor-name TestMonitor \
        --query-id AQICAHjE50ADcWtUTXGTlgtIHH4U_u4xxxxxx

Output::

    {
        "Fields": [{
            "Name": "timestamp",
            "Type": "integer"
        }, {
            "Name": "availability",
            "Type": "float"
        }, {
            "Name": "performance",
            "Type": "float"
        }, {
            "Name": "rtt_p50",
            "Type": "bigint"
        }, {
            "Name": "rtt_p90",
            "Type": "bigint"
        }, {
            "Name": "rtt_p95",
            "Type": "bigint"
        }, {
            "Name": "bytes_in",
            "Type": "bigint"
        }, {
            "Name": "bytes_out",
            "Type": "bigint"
        }],
        "Data": [
            ["1724833200", "100.0", "100.0", "26", "68", "72", "1258", "120"]
        ]
    }

For more information, see `Use the Internet Monitor query interface <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-IM-view-cw-tools-cwim-query.html>`__ in the *Amazon CloudWatch User Guide*.
